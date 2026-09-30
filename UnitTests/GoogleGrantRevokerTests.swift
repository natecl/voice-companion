import XCTest

final class GoogleGrantRevokerTests: XCTestCase {
    func testRevocationUsesFixedHTTPSPostAndEncodedBody() async throws {
        let revoker = GoogleGrantRevoker { request in
            XCTAssertEqual(request.url?.absoluteString, "https://oauth2.googleapis.com/revoke")
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/x-www-form-urlencoded")
            XCTAssertEqual(request.timeoutInterval, 15)
            XCTAssertEqual(String(data: request.httpBody!, encoding: .utf8), "token=fixture%2B%2F%3D%26token%3Dother")
            return (Data(), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }
        try await revoker.revoke("fixture+/=&token=other")
    }

    func testInvalidTokensNeverReachNetwork() async {
        let revoker = GoogleGrantRevoker { _ in XCTFail("Sent invalid token"); throw AccountFailure.unavailable }
        for token in ["", "bad token", String(repeating: "x", count: 8193)] {
            do { try await revoker.revoke(token); XCTFail("Accepted invalid token") } catch {}
        }
    }

    func testProviderFailuresNeverClaimRevocationOrExposeBody() async {
        for status in [302, 400, 401, 429, 500] {
            let revoker = GoogleGrantRevoker { request in
                (Data("private-provider-body".utf8), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
            }
            do { try await revoker.revoke("fictional-grant"); XCTFail("Accepted \(status)") }
            catch { XCTAssertFalse(error.localizedDescription.contains("private-provider-body")) }
        }
    }

    func testInvalidGrantRequestsReauthenticationInsteadOfClaimingSuccess() async {
        let revoker = GoogleGrantRevoker { request in
            (Data(#"{"error":"invalid_token"}"#.utf8), HTTPURLResponse(url: request.url!, statusCode: 400, httpVersion: nil, headerFields: nil)!)
        }
        do { try await revoker.revoke("fictional-grant"); XCTFail() }
        catch AccountFailure.providerGrantExpired {} catch { XCTFail("Wrong failure classification") }
    }

    func testFreshGrantAfterErasureCannotTargetAnotherIdentityOrReopenServerPhase() throws {
        let account = StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google,
            session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                                    owner: UUID().uuidString, expires: 100, refreshExpires: 200),
            googleGrant: GoogleAccountGrant(subject: "original", token: "original-grant"))
        var pending = PendingAccountDeletion(account: account)
        XCTAssertThrowsError(try pending.replacingGoogleGrant(.init(subject: "original", token: "fresh-grant")))
        pending.serverDeleted = true
        XCTAssertThrowsError(try pending.replacingGoogleGrant(.init(subject: "other", token: "other-grant")))
        let fresh = try pending.replacingGoogleGrant(.init(subject: "original", token: "fresh-grant"))
        XCTAssertTrue(fresh.serverDeleted)
        XCTAssertEqual(fresh.id, pending.id)
        XCTAssertEqual(fresh.owner, pending.owner)
        XCTAssertEqual(fresh.googleGrant?.token, "fresh-grant")
    }

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
