import Foundation

struct PendingAccountDeletion: Codable, Sendable, Equatable {
    enum Credential: String, Codable, Sendable { case session, recovery }
    let id: UUID
    let endpoint: URL
    let provider: AccountProvider
    let owner: String
    let token: String
    let credential: Credential
    var serverDeleted: Bool

    init(account: StoredAccount) {
        id = UUID(); endpoint = account.endpoint; provider = account.provider
        owner = account.session.owner; token = account.session.refreshToken
        credential = .session; serverDeleted = false
    }

    init(endpoint: URL, provider: AccountProvider, receipt: AccountDeletionReceipt) {
        id = UUID(); self.endpoint = endpoint; self.provider = provider
        owner = receipt.owner; token = receipt.deletionToken
        credential = .recovery; serverDeleted = false
    }

    func validate() throws {
        _ = try AccountTransport(endpoint: endpoint)
        guard UUID(uuidString: owner) != nil, (32...256).contains(token.utf8.count),
              !token.contains(where: { $0.isWhitespace }) else { throw AccountFailure.invalidResponse }
    }
}

struct AccountDeletionReceipt: Decodable, Sendable {
    let status: String
    let owner: String
    let deletionToken: String
    enum CodingKeys: String, CodingKey { case status, owner; case deletionToken = "deletion_token" }
}

protocol AccountDeleting: Sendable {
    func deleteAccount(_ refreshToken: String) async throws
    func resumeDeletion(_ deletionToken: String) async throws
}
extension AccountTransport: AccountDeleting {}

/// Durable server completion precedes local cleanup. A retry after a local disk or
/// Keychain failure never needs another provider call. All local stores write on
/// the main actor, so cleanup cannot interleave with their synchronous file writes.
@MainActor
final class AccountDeletionController {
    private var busy = false
    private let load: () throws -> PendingAccountDeletion?
    private let save: (PendingAccountDeletion) throws -> Void
    private let complete: (UUID) throws -> Void
    private let erase: @MainActor (String) throws -> Void
    private let transport: (URL) throws -> any AccountDeleting

    init(load: @escaping () throws -> PendingAccountDeletion? = AccountCredentialStore.pendingDeletion,
         save: @escaping (PendingAccountDeletion) throws -> Void = AccountCredentialStore.saveDeletion,
         complete: @escaping (UUID) throws -> Void = AccountCredentialStore.completeDeletion,
         erase: @escaping @MainActor (String) throws -> Void = LocalAccountErasure.erase,
         transport: @escaping (URL) throws -> any AccountDeleting = { try AccountTransport(endpoint: $0) }) {
        self.load = load; self.save = save; self.complete = complete
        self.erase = erase; self.transport = transport
    }

    func finish(_ original: PendingAccountDeletion) async throws {
        guard !busy else { throw AccountFailure.unavailable }
        busy = true
        defer { busy = false }
        try original.validate()
        guard var pending = try load(), pending.id == original.id else { throw AccountFailure.cancelled }
        if !pending.serverDeleted {
            let service = try transport(pending.endpoint)
            switch pending.credential {
            case .session: try await service.deleteAccount(pending.token)
            case .recovery: try await service.resumeDeletion(pending.token)
            }
            guard try load()?.id == pending.id else { throw AccountFailure.cancelled }
            pending.serverDeleted = true
            try save(pending)
        }
        guard try load()?.id == pending.id else { throw AccountFailure.cancelled }
        try erase(pending.owner)
        try complete(pending.id)
    }
}
