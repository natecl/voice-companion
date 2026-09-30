import Foundation
import CryptoKit

/// Operator-staged, one-time migration. Ordinary enrollment never creates a plan.
/// The server must first bind the verified Google identity to the preserved owner.
struct FounderAccountMigration: Codable, Equatable {
    static let filename = "founder-google-migration.json"
    let version: Int
    let owner: String
    let endpoint: URL
    let sessions: [String: String]
    let outbox: [String: String]

    static var appBase: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .resolvingSymlinksInPath().appendingPathComponent("VoiceCompanion")
    }

    static func pending(base: URL = appBase) throws -> Self? {
        let file = base.appendingPathComponent(filename)
        guard FileManager.default.fileExists(atPath: file.path) else { return nil }
        try requirePlainPath(file, base: base)
        let plan = try JSONDecoder().decode(Self.self, from: Data(contentsOf: file))
        guard plan.version == 1, UUID(uuidString: plan.owner) != nil, !plan.sessions.isEmpty else {
            throw AccountFailure.invalidResponse
        }
        _ = try AccountTransport(endpoint: plan.endpoint)
        for files in [plan.sessions, plan.outbox] {
            guard files.allSatisfy({ name, hash in
                name == URL(fileURLWithPath: name).lastPathComponent && name.hasSuffix(".json") &&
                hash.count == 64 && hash.allSatisfy({ "0123456789abcdef".contains($0) })
            }) else { throw AccountFailure.invalidResponse }
        }
        return plan
    }

    func validate(account: StoredAccount) throws {
        guard account.provider == .google, account.endpoint == endpoint,
              account.session.owner == owner else { throw AccountFailure.signInRequired }
        try account.session.validate()
    }

    /// A directory rename preserves original bytes. If interrupted after rename,
    /// the same verified plan accepts only the exact destination on the next run.
    func prepareStorage(account: StoredAccount, base: URL = appBase) throws {
        try validate(account: account)
        guard try Self.pending(base: base) == self else { throw AccountFailure.invalidResponse }
        let source = base.appendingPathComponent("sessions")
        let parent = base.appendingPathComponent("accounts").appendingPathComponent(owner)
        let destination = parent.appendingPathComponent("sessions")
        let outboxDirectory = base.appendingPathComponent("memory-outbox").appendingPathComponent(owner)
        for path in [source, parent, destination, outboxDirectory] { try Self.requirePlainPath(path, base: base) }
        for path in [parent, outboxDirectory] {
            guard !FileManager.default.fileExists(atPath: path.appendingPathComponent(LocalAccountErasure.marker).path) else {
                throw AccountFailure.signInRequired
            }
        }
        try verify(directory: outboxDirectory, hashes: outbox, base: base)
        let sourceExists = FileManager.default.fileExists(atPath: source.path)
        let targetExists = FileManager.default.fileExists(atPath: destination.path)
        guard sourceExists != targetExists else { throw AccountFailure.invalidResponse }
        let selected = sourceExists ? source : destination
        try verify(directory: selected, hashes: sessions, base: base)
        // Preserve interrupted recordings too; the normal recovery controller
        // handles them after activation. Startup has not opened a controller yet.
        _ = try SessionStore(directory: selected, expectedOwner: owner).load()
        if sourceExists {
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: true)
            try FileManager.default.moveItem(at: source, to: destination)
        }
        try verify(directory: destination, hashes: sessions, base: base)
    }

    /// Called only after the accepted account has been durably installed. Keep
    /// the plan on any failure so startup cannot fall back to legacy capture.
    func finish(account: StoredAccount, base: URL = appBase) throws {
        try prepareStorage(account: account, base: base)
        try FileManager.default.removeItem(at: base.appendingPathComponent(Self.filename))
    }

    private func verify(directory: URL, hashes: [String: String], base: URL) throws {
        let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        guard Set(files.map(\.lastPathComponent)) == Set(hashes.keys) else { throw AccountFailure.invalidResponse }
        for file in files {
            try Self.requirePlainPath(file, base: base)
            let hash = SHA256.hash(data: try Data(contentsOf: file)).map { String(format: "%02x", $0) }.joined()
            guard hashes[file.lastPathComponent] == hash else { throw AccountFailure.invalidResponse }
        }
    }

    private static func requirePlainPath(_ path: URL, base: URL) throws {
        // Inspect every component within the app-owned root, including missing
        // destinations' existing parents. System aliases above it (e.g. /var)
        // are supplied by Application Support and are not migration redirects.
        let root = base.standardizedFileURL
        var ancestor = path.standardizedFileURL
        guard ancestor.path.hasPrefix(root.path + "/") else { throw AccountFailure.invalidResponse }
        while true {
            if let attributes = try? FileManager.default.attributesOfItem(atPath: ancestor.path),
               attributes[.type] as? FileAttributeType == .typeSymbolicLink {
                throw AccountFailure.invalidResponse
            }
            if ancestor.path == root.path { break }
            ancestor.deleteLastPathComponent()
        }
    }
}
