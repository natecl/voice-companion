#if DEBUG && os(iOS)
import SwiftUI

/// Device Keychain + filesystem lifecycle fixture. The launch ID isolates both
/// stores. Server requests are fictional and never call providers.
struct AccountDeletionKeychainFixture: View {
    @State private var result = "Checking fixture"

    var body: some View {
        Text(result).task {
            do { result = try await run() }
            catch { result = "Fixture failed" }
        }
    }

    @MainActor private func run() async throws -> String {
        guard let raw = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_ID"], UUID(uuidString: raw) != nil else { throw AccountFailure.invalidResponse }
        let owner = raw
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let base = support.appendingPathComponent("account-erasure-qa").appendingPathComponent(owner)
        let cache = RecordingNotesCache(directory: base.appendingPathComponent("cache"))
        let store = SessionStore(directory: base.appendingPathComponent("accounts").appendingPathComponent(owner).appendingPathComponent("sessions"), expectedOwner: owner)
        let networkJSON = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_NETWORK"]
        let networkAccount = try networkJSON.map { try JSONDecoder().decode(StoredAccount.self, from: Data($0.utf8)) }
        if let networkAccount {
            guard networkAccount.endpoint.scheme == "wss", networkAccount.endpoint.host == "127.0.0.1",
                  networkAccount.session.owner == owner, networkAccount.googleGrant?.token == "fictional-google-grant" else { throw AccountFailure.invalidResponse }
        }
        let makeTransport: (URL) throws -> any AccountDeleting = { endpoint in
            if networkAccount != nil { return try AccountTransport(endpoint: endpoint) }
            return FictionalDeletion()
        }
        let phase = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_PHASE"]
        if phase == "prepare" {
            guard try !AccountCredentialStore.hasEnrollmentState() else { throw AccountFailure.invalidResponse }
            let account = networkAccount ?? StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google,
                session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64), owner: owner,
                                        expires: Date.now.timeIntervalSince1970 + 3600, refreshExpires: Date.now.timeIntervalSince1970 + 86400),
                googleGrant: GoogleAccountGrant(subject: "fictional-google-subject", token: "fictional-google-grant"))
            let manager = AccountSessionManager(account: nil)
            try await manager.install(account)
            var session = CaptureSession(id: UUID(), createdAt: .now)
            session.memoryOwnerID = owner
            try store.save(session)
            let pending = try await manager.prepareDeletion()
            let controller = AccountDeletionController(erase: { _ in
                if networkAccount == nil { throw AccountFailure.unavailable }
                try LocalAccountErasure.erase(owner: owner, base: base, cache: cache)
            }, transport: makeTransport)
            do { try await controller.finish(pending); throw AccountFailure.invalidResponse }
            catch AccountFailure.unavailable {}
            guard try AccountCredentialStore.load() == nil,
                  try AccountCredentialStore.pendingDeletion()?.serverDeleted == true else { throw AccountFailure.invalidResponse }
            return "Pending erasure saved"
        }
        if phase == "finish" {
            guard let pending = try AccountCredentialStore.pendingDeletion(), pending.owner == owner, pending.serverDeleted,
                  pending.googleGrant == GoogleAccountGrant(subject: "fictional-google-subject", token: "fictional-google-grant"),
                  try store.load().count == (networkAccount == nil ? 1 : 0), try AccountCredentialStore.load() == nil else { throw AccountFailure.invalidResponse }
            let controller = AccountDeletionController(erase: { erasedOwner in
                guard erasedOwner == owner else { throw AccountFailure.invalidResponse }
                try LocalAccountErasure.erase(owner: owner, base: base, cache: cache)
            }, transport: makeTransport)
            try await controller.finish(pending)
            guard try store.load().isEmpty else { throw AccountFailure.invalidResponse }
            return "Erased and signed out"
        }
        guard phase == "verify", try AccountCredentialStore.hasEnrollmentState(),
              try AccountCredentialStore.load() == nil, try AccountCredentialStore.pendingDeletion() == nil,
              try store.load().isEmpty else { throw AccountFailure.invalidResponse }
        return "Signed out after relaunch"
    }

    private struct FictionalDeletion: AccountDeleting {
        func finishGoogleDeletion(_ credential: String, kind: PendingAccountDeletion.Credential, grant: String) async throws {
            guard grant == "fictional-google-grant" else { throw AccountFailure.invalidResponse }
        }
        func deleteAccount(_ refreshToken: String) async throws -> AccountDeletionStatus { .awaitingGoogleRevocation }
        func resumeDeletion(_ deletionToken: String) async throws -> AccountDeletionStatus { throw AccountFailure.invalidResponse }
    }
}
#endif
