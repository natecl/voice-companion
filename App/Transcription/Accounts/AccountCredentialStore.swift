import Foundation
import Security

/// Separate from the founder's legacy relay credential. One atomic Keychain item
/// contains the endpoint, provider and rotating tokens; nothing enters defaults.
struct StoredAccount: Codable, Sendable {
    let endpoint: URL
    let provider: AccountProvider
    let session: AccountSession
    var googleGrant: GoogleAccountGrant? = nil
}

private struct AccountKeychainState: Codable {
    var account: StoredAccount?
    var deletion: PendingAccountDeletion? = nil
}

enum AccountCredentialStore {
    private static var query: [String: Any] {
        var service = (Bundle.main.bundleIdentifier ?? "ai.voicecompanion") + ".accounts"
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--account-keychain-fixture") {
            // Every fixture has a separate Keychain service, even for malformed
            // launch input. It can never read or replace real enrollment state.
            let raw = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_ID"] ?? "invalid"
            service += ".qa." + (UUID(uuidString: raw)?.uuidString ?? "invalid")
        }
        #endif
        return [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: "session-v1",
         kSecAttrSynchronizable as String: false]
    }

    static func save(_ account: StoredAccount) throws {
        _ = try AccountTransport(endpoint: account.endpoint)
        try account.session.validate()
        try account.googleGrant?.validate()
        guard try read()?.deletion == nil else { throw AccountFailure.deletionPending }
        try write(AccountKeychainState(account: account))
    }

    private static func write(_ state: AccountKeychainState) throws {
        let values: [String: Any] = [
            kSecValueData as String: try JSONEncoder().encode(state),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let result = SecItemUpdate(query as CFDictionary, values as CFDictionary)
        if result == errSecItemNotFound {
            guard SecItemAdd(query.merging(values) { _, value in value } as CFDictionary, nil) == errSecSuccess else {
                throw AccountFailure.unavailable
            }
        } else if result != errSecSuccess { throw AccountFailure.unavailable }
    }

    static func hasEnrollmentState() throws -> Bool { try read() != nil }

    static func load() throws -> StoredAccount? {
        guard let account = try read()?.account else { return nil }
        _ = try AccountTransport(endpoint: account.endpoint)
        guard UUID(uuidString: account.session.owner) != nil else { throw AccountFailure.invalidResponse }
        return account
    }

    private static func read() throws -> AccountKeychainState? {
        var lookup = query
        lookup[kSecReturnData as String] = true
        lookup[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(lookup as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw AccountFailure.unavailable }
        return try JSONDecoder().decode(AccountKeychainState.self, from: data)
    }

    static func pendingDeletion() throws -> PendingAccountDeletion? {
        let pending = try read()?.deletion
        try pending?.validate()
        return pending
    }

    static func saveDeletion(_ pending: PendingAccountDeletion) throws {
        try pending.validate()
        let state = try read()
        if let active = state?.account, active.session.owner != pending.owner { throw AccountFailure.signInRequired }
        if let prior = state?.deletion, prior.owner != pending.owner { throw AccountFailure.deletionPending }
        try write(AccountKeychainState(account: nil, deletion: pending))
    }

    static func completeDeletion(_ id: UUID) throws {
        guard let state = try read(), state.account == nil, state.deletion?.id == id else { throw AccountFailure.cancelled }
        try write(AccountKeychainState(account: nil))
    }

    static func clear() throws {
        // Keep a durable signed-out marker: never fall back to the legacy owner.
        try write(AccountKeychainState(account: nil, deletion: try read()?.deletion))
    }
}
