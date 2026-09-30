#if DEBUG && os(iOS)
import SwiftUI
import CryptoKit

/// Isolated simulator driver for actual AccountRuntime startup and Keychain.
/// No provider UI or network; synthetic account expiry remains an hour away.
struct FounderMigrationKeychainFixture: View {
    @State private var result = "Checking migration"
    var body: some View {
        Text(result).task {
            do { result = try await run() }
            catch { result = "Migration fixture failed" }
        }
    }

    @MainActor private func run() async throws -> String {
        guard ProcessInfo.processInfo.arguments.contains("--account-keychain-fixture"),
              let owner = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_ID"],
              UUID(uuidString: owner) != nil else { throw AccountFailure.invalidResponse }
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let base = support.appendingPathComponent("founder-migration-qa").appendingPathComponent(owner)
        let endpoint = URL(string: "wss://example.com/account")!
        func account(_ provider: AccountProvider = .google, owner selected: String? = nil) -> StoredAccount {
            StoredAccount(endpoint: endpoint, provider: provider,
                session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                    owner: selected ?? owner, expires: Date.now.timeIntervalSince1970 + 3600,
                    refreshExpires: Date.now.timeIntervalSince1970 + 86400))
        }
        let phase = ProcessInfo.processInfo.environment["ELLIS_ACCOUNT_QA_PHASE"]
        if phase == "prepare" {
            guard try !AccountCredentialStore.hasEnrollmentState(),
                  !FileManager.default.fileExists(atPath: base.path) else { throw AccountFailure.invalidResponse }
            var source = CaptureSession(id: UUID(), createdAt: .now)
            source.memoryOwnerID = owner
            try SessionStore(directory: base.appendingPathComponent("sessions")).save(source)
            let file = base.appendingPathComponent("sessions").appendingPathComponent(source.id.uuidString + ".json")
            let hash = SHA256.hash(data: try Data(contentsOf: file)).map { String(format: "%02x", $0) }.joined()
            try FileManager.default.createDirectory(at: base.appendingPathComponent("memory-outbox").appendingPathComponent(owner), withIntermediateDirectories: true)
            let plan = FounderAccountMigration(version: 1, owner: owner, endpoint: endpoint, sessions: [file.lastPathComponent: hash], outbox: [:])
            try JSONEncoder().encode(plan).write(to: base.appendingPathComponent(FounderAccountMigration.filename))
            for wrong in [account(.apple), account(owner: UUID().uuidString)] {
                try AccountCredentialStore.save(wrong)
                let runtime = AccountRuntime(migrationBase: base)
                await runtime.restore()
                guard runtime.ready, !runtime.legacy, runtime.active == nil,
                      FileManager.default.fileExists(atPath: file.path),
                      try FounderAccountMigration.pending(base: base) != nil else { throw AccountFailure.invalidResponse }
            }
            try AccountCredentialStore.clear()
            try plan.prepareStorage(account: account(), base: base)
            return "Wrong accounts blocked; move interrupted"
        }
        if phase == "pending" {
            let runtime = AccountRuntime(migrationBase: base)
            await runtime.restore()
            guard runtime.ready, !runtime.legacy, runtime.active == nil,
                  try AccountCredentialStore.load() == nil,
                  try FounderAccountMigration.pending(base: base) != nil else { throw AccountFailure.invalidResponse }
            // Model interruption after successful enrollment's Keychain commit.
            try AccountCredentialStore.save(account())
            return "Pending move survived; account saved"
        }
        guard phase == "finish" || phase == "verify" else { throw AccountFailure.invalidResponse }
        let runtime = AccountRuntime(migrationBase: base)
        await runtime.restore()
        guard runtime.ready, !runtime.legacy, runtime.active?.session.owner == owner,
              runtime.active?.provider == .google, runtime.message == nil,
              try FounderAccountMigration.pending(base: base) == nil,
              try AccountCredentialStore.load()?.session.owner == owner else { throw AccountFailure.invalidResponse }
        let store = SessionStore(directory: base.appendingPathComponent("accounts").appendingPathComponent(owner).appendingPathComponent("sessions"), expectedOwner: owner)
        guard try store.load().count == 1,
              !FileManager.default.fileExists(atPath: base.appendingPathComponent("sessions").path) else { throw AccountFailure.invalidResponse }
        return phase == "finish" ? "Migration restored from Keychain" : "Google account persisted after relaunch"
    }
}
#endif
