import Foundation

/// Minimal tombstones block old controllers from recreating erased content.
/// Only managed owner folders are touched; legacy/founder data stays separate.
@MainActor
enum LocalAccountErasure {
    nonisolated static let marker = ".account-deleted"

    static func erase(owner: String) throws {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try erase(owner: owner, base: support.appendingPathComponent("VoiceCompanion"), cache: .shared)
    }

    static func erase(owner: String, base: URL, cache: RecordingNotesCache) throws {
        guard UUID(uuidString: owner) != nil else { throw AccountFailure.invalidResponse }
        let folders = [base.appendingPathComponent("accounts").appendingPathComponent(owner),
                       base.appendingPathComponent("memory-outbox").appendingPathComponent(owner)]
        for folder in folders {
            let expected = folder.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(owner).standardizedFileURL
            guard folder.resolvingSymlinksInPath().standardizedFileURL == expected else { throw AccountFailure.invalidResponse }
        }
        // Write both barriers before removing content. Repeating this is safe
        // after a partial disk failure; do not remove these barriers on sign-out.
        for folder in folders {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try Data().write(to: folder.appendingPathComponent(marker), options: .atomic)
        }
        try cache.erase(owner: owner)
        for folder in folders {
            for item in try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil)
                where item.lastPathComponent != marker {
                try FileManager.default.removeItem(at: item)
            }
        }
    }
}
