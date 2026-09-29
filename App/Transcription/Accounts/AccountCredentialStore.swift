import Foundation
import Security

/// Separate from the founder's legacy relay credential. One atomic Keychain item
/// contains the endpoint, provider and rotating tokens; nothing enters defaults.
struct StoredAccount: Codable, Sendable {
    let endpoint: URL
    let provider: AccountProvider
    let session: AccountSession
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
        let values: [String: Any] = [
            kSecValueData as String: try JSONEncoder().encode(account),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let result = SecItemUpdate(query as CFDictionary, values as CFDictionary)
        if result == errSecItemNotFound {
            guard SecItemAdd(query.merging(values) { _, value in value } as CFDictionary, nil) == errSecSuccess else {
                throw AccountFailure.unavailable
            }
        } else if result != errSecSuccess { throw AccountFailure.unavailable }
    }

    static func load() throws -> StoredAccount? {
        var lookup = query
        lookup[kSecReturnData as String] = true
        lookup[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(lookup as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw AccountFailure.unavailable }
        let account = try JSONDecoder().decode(StoredAccount.self, from: data)
        _ = try AccountTransport(endpoint: account.endpoint)
        // Expired access is deliberately retained so it can be refreshed.
        guard UUID(uuidString: account.session.owner) != nil else { throw AccountFailure.invalidResponse }
        return account
    }

    static func clear() throws {
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw AccountFailure.unavailable }
    }
}
