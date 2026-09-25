import Foundation
import Security

/// Device-local internal enrollment. No provider key, iCloud synchronization, or plaintext preferences.
enum RelayCredentialStore {
    private static var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: (Bundle.main.bundleIdentifier ?? "ai.voicecompanion") + ".relay",
         kSecAttrAccount as String: "hosted-v1",
         kSecAttrSynchronizable as String: false]
    }

    static func save(_ config: RelayConfiguration) throws {
        try config.validateHosted()
        let values: [String: Any] = [
            kSecValueData as String: try JSONEncoder().encode(config),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let updated = SecItemUpdate(query as CFDictionary, values as CFDictionary)
        if updated == errSecItemNotFound {
            let status = SecItemAdd(query.merging(values) { _, new in new } as CFDictionary, nil)
            guard status == errSecSuccess else { throw storageError(status) }
        } else if updated != errSecSuccess { throw storageError(updated) }
    }

    static func load() throws -> RelayConfiguration? {
        var lookup = query
        lookup[kSecReturnData as String] = true
        lookup[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(lookup as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw storageError(status) }
        return try JSONDecoder().decode(RelayConfiguration.self, from: data)
    }

    private static func storageError(_ status: OSStatus) -> NSError {
        NSError(domain: NSOSStatusErrorDomain, code: Int(status),
                userInfo: [NSLocalizedDescriptionKey: "Secure recording configuration is unavailable. Unlock the device and try again."])
    }
}
