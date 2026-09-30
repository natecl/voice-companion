import Foundation

protocol AccountRefreshing: Sendable {
    func refresh(_ token: String) async throws -> AccountSession
}
extension AccountTransport: AccountRefreshing {}

/// Serializes refresh across capture/chat/sync. Generation checks discard responses
/// arriving after local sign-out or another completed login.
actor AccountSessionManager {
    static let shared = AccountSessionManager(account: nil)
    // Covers the five-minute capture cap plus connection/finalization headroom.
    private static let refreshLeadSeconds: TimeInterval = 600
    private var account: StoredAccount?
    private var generation = UUID()
    private var refreshTask: Task<StoredAccount, Error>?
    private let save: @Sendable (StoredAccount) throws -> Void
    private let clear: @Sendable () throws -> Void
    private let makeTransport: @Sendable (URL) throws -> any AccountRefreshing

    init(account: StoredAccount?,
         save: @escaping @Sendable (StoredAccount) throws -> Void = AccountCredentialStore.save,
         clear: @escaping @Sendable () throws -> Void = AccountCredentialStore.clear,
         makeTransport: @escaping @Sendable (URL) throws -> any AccountRefreshing = { try AccountTransport(endpoint: $0) }) {
        self.account = account
        self.save = save
        self.clear = clear
        self.makeTransport = makeTransport
    }

    func install(_ value: StoredAccount, restoring: Bool = false) throws {
        try value.session.validate(now: restoring ? .distantPast : .now)
        _ = try AccountTransport(endpoint: value.endpoint)
        // Owner changes require the UI/controller teardown and explicit sign-out.
        if let account, account.session.owner != value.session.owner { throw AccountFailure.signInRequired }
        if !restoring { try save(value) }
        generation = UUID()
        refreshTask?.cancel()
        refreshTask = nil
        account = value
    }

    func current(now: Date = .now) async throws -> StoredAccount {
        guard let account else { throw AccountFailure.signInRequired }
        guard account.session.refreshExpires > now.timeIntervalSince1970 else {
            _ = try removeLocalAccount()
            throw AccountFailure.signInRequired
        }
        if account.session.expires > now.timeIntervalSince1970 + Self.refreshLeadSeconds { return account }
        if let refreshTask { return try await refreshTask.value }
        let expected = generation
        let task = Task { try await self.rotate(account, generation: expected) }
        refreshTask = task
        return try await task.value
    }

    private func rotate(_ previous: StoredAccount, generation expected: UUID) async throws -> StoredAccount {
        do {
            let transport = try makeTransport(previous.endpoint)
            let session = try await transport.refresh(previous.session.refreshToken)
            guard generation == expected else { throw AccountFailure.cancelled }
            try session.validate()
            guard session.owner == previous.session.owner else { throw AccountFailure.invalidResponse }
            let next = StoredAccount(endpoint: previous.endpoint, provider: previous.provider, session: session)
            try save(next)
            account = next
            refreshTask = nil
            return next
        } catch {
            if generation == expected {
                // An uncertain rotation must not reuse the old refresh token.
                // Drop access in memory even if Keychain is temporarily locked.
                account = nil
                generation = UUID()
                refreshTask = nil
                try? clear()
            }
            throw error
        }
    }

    /// Caller stops account-owned work before this, then revokes the returned
    /// refresh credential through the service. A failed secure clear is explicit.
    func removeLocalAccount() throws -> StoredAccount? {
        let previous = account
        generation = UUID()
        refreshTask?.cancel()
        refreshTask = nil
        account = nil
        try clear()
        return previous
    }
}
