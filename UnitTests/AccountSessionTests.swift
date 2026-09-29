import XCTest

private actor RefreshFixture: AccountRefreshing {
    var calls = 0
    let response: AccountSession
    var continuation: CheckedContinuation<AccountSession, Error>?
    init(_ response: AccountSession) { self.response = response }
    func refresh(_ token: String) async throws -> AccountSession {
        calls += 1
        return try await withCheckedThrowingContinuation { continuation = $0 }
    }
    func waitForRequest() async { while calls == 0 { await Task.yield() } }
    func complete() { continuation?.resume(returning: response); continuation = nil }
}

@MainActor
final class AccountSessionTests: XCTestCase {
    func session(owner: String, expired: Bool = false) -> AccountSession {
        AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                       owner: owner, expires: Date.now.timeIntervalSince1970 + (expired ? -1 : 3600),
                       refreshExpires: Date.now.timeIntervalSince1970 + 86400)
    }
    func stored(_ session: AccountSession) -> StoredAccount {
        StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google, session: session)
    }

    func testConcurrentRequestsShareOneRefresh() async throws {
        let owner = UUID().uuidString
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: stored(session(owner: owner, expired: true)),
                                            save: { _ in }, clear: {}, makeTransport: { _ in fixture })
        let first = Task { try await manager.current() }
        await fixture.waitForRequest()
        let second = Task { try await manager.current() }
        await fixture.complete()
        let a = try await first.value
        let b = try await second.value
        XCTAssertEqual(a.session.owner, b.session.owner)
        let count = await fixture.calls
        XCTAssertEqual(count, 1)
    }

    func testLateRefreshCannotRestoreSignedOutAccount() async throws {
        let owner = UUID().uuidString
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: stored(session(owner: owner, expired: true)),
                                            save: { _ in XCTFail("Stale session was saved") }, clear: {},
                                            makeTransport: { _ in fixture })
        let request = Task { try await manager.current() }
        await fixture.waitForRequest()
        _ = try await manager.removeLocalAccount()
        await fixture.complete()
        do { _ = try await request.value; XCTFail("Stale refresh succeeded") } catch {}
        do { _ = try await manager.current(); XCTFail("Account restored") } catch {}
    }

    func testOwnerSwitchRequiresTeardownAndSignOut() async throws {
        let manager = AccountSessionManager(account: stored(session(owner: UUID().uuidString)), save: { _ in }, clear: {})
        do { try await manager.install(stored(session(owner: UUID().uuidString))); XCTFail("Switched owner") } catch {}
        _ = try await manager.removeLocalAccount()
        let next = stored(session(owner: UUID().uuidString))
        try await manager.install(next)
        let actual = try await manager.current()
        XCTAssertEqual(actual.session.owner, next.session.owner)
    }

    func testTransportRejectsUnencryptedOrCredentialBearingEndpoints() {
        for value in ["ws://example.com/account", "wss://example.com/stt", "wss://user:secret@example.com/account",
                      "wss://example.com/account?token=x", "wss://example.com/account#x"] {
            XCTAssertThrowsError(try AccountTransport(endpoint: URL(string: value)!))
        }
    }
}
