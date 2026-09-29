import Foundation
import Security

/// Separate from the founder's legacy relay credential. One atomic Keychain item
/// contains the endpoint, provider and rotating tokens; nothing enters defaults.
struct StoredAccount: Codable, Sendable {
    let endpoint: URL
    let provider: AccountProvider
    let session: AccountSession
}

private struct AccountKeychainState: Codable {
    var account: StoredAccount?
}

enum AccountCredentialStore {
    private static var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: (Bundle.main.bundleIdentifier ?? "ai.voicecompanion") + ".accounts",
         kSecAttrAccount as String: "session-v1",
         kSecAttrSynchronizable as String: false]
    }

    static func save(_ account: StoredAccount) throws {
        _ = try AccountTransport(endpoint: account.endpoint)
        try account.session.validate()
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

    static func clear() throws {
        // Keep a durable signed-out marker: never fall back to the legacy owner.
        try write(AccountKeychainState(account: nil))
    }
}
