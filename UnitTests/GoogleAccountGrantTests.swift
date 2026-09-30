import XCTest

final class GoogleAccountGrantTests: XCTestCase {
    func testExistingCredentialEncodingRemainsReadable() throws {
        let owner = UUID().uuidString
        let account = StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google,
            session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                                    owner: owner, expires: 100, refreshExpires: 200))
        let data = try JSONEncoder().encode(account)
        XCTAssertNil(try JSONDecoder().decode(StoredAccount.self, from: data).googleGrant)
        let pending = PendingAccountDeletion(account: account)
        var old = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(pending)) as? [String: Any])
        old.removeValue(forKey: "googleRevoked"); old.removeValue(forKey: "googleGrant")
        let restored = try JSONDecoder().decode(PendingAccountDeletion.self, from: JSONSerialization.data(withJSONObject: old))
        XCTAssertEqual(restored.owner, owner)
        XCTAssertNil(restored.googleRevoked)
    }
}
