import Foundation
import CryptoKit

/// Ready summaries only. Disk keys include all source identity, never credentials.
@MainActor
final class RecordingNotesCache {
    static let shared = RecordingNotesCache(directory: FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("RecordingNotesCache"))

    struct Key: Codable, Hashable, Sendable {
        let owner: String
        let sessionID: String
        let revision: Int
    }
    private struct Entry: Codable {
        let schemaVersion: Int
        let key: Key
        let generationVersion: String
        let result: RecordingNotesResult
    }
    private struct Flight { let id: UUID; let task: Task<RecordingNotesResult?, Error> }
    private let directory: URL
    private var flights: [Key: Flight] = [:]
    private var values: [Key: RecordingNotesResult] = [:]

    init(directory: URL) { self.directory = directory }

    private func digest(_ value: String) -> String {
        SHA256.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    private func ownerDirectory(_ owner: String) -> URL { directory.appendingPathComponent(digest(owner)) }
    private func sourceDirectory(_ key: Key) -> URL { ownerDirectory(key.owner).appendingPathComponent(digest(key.sessionID)) }
    private func file(_ key: Key) -> URL { sourceDirectory(key).appendingPathComponent("\(key.revision).json") }

    /// Persist the highest known transcript revision, so an old view/late request cannot revive it.
    private func acceptRevision(_ key: Key) throws -> Bool {
        let folder = sourceDirectory(key)
        let marker = folder.appendingPathComponent("revision")
        let known = (try? String(contentsOf: marker, encoding: .utf8)).flatMap(Int.init)
        if let known, key.revision < known { return false }
        if known != key.revision {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try Data(String(key.revision).utf8).write(to: marker, options: .atomic)
            for (other, flight) in flights where other.owner == key.owner && other.sessionID == key.sessionID && other.revision != key.revision {
                flight.task.cancel(); flights[other] = nil
            }
            values = values.filter { $0.key.owner != key.owner || $0.key.sessionID != key.sessionID || $0.key.revision == key.revision }
            for url in try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil) where url.pathExtension == "json" && url != file(key) {
                try FileManager.default.removeItem(at: url)
            }
        }
        return true
    }

    /// Synchronous local read lets presentation render before starting its refresh.
    func read(_ key: Key) throws -> RecordingNotesResult? {
        guard try acceptRevision(key) else { return nil }
        if let result = values[key] { return result }
        let url = file(key)
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        let entry = try JSONDecoder().decode(Entry.self, from: Data(contentsOf: url))
        guard entry.schemaVersion == 1, entry.key == key, entry.generationVersion == entry.result.generation_version, valid(entry.result, for: key) else { return nil }
        values[key] = entry.result
        return entry.result
    }

    private func valid(_ result: RecordingNotesResult, for key: Key) -> Bool {
        result.state == "ready" && result.notes != nil && result.revision == key.revision && !result.generation_version.isEmpty
    }

    func store(_ result: RecordingNotesResult, for key: Key) throws {
        guard valid(result, for: key), try acceptRevision(key) else { return }
        let folder = sourceDirectory(key)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        var protectedFolder = folder
        var attributes = URLResourceValues(); attributes.isExcludedFromBackup = true
        try protectedFolder.setResourceValues(attributes)
        let data = try JSONEncoder().encode(Entry(schemaVersion: 1, key: key, generationVersion: result.generation_version, result: result))
        #if os(iOS)
        try data.write(to: file(key), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        #else
        try data.write(to: file(key), options: .atomic)
        #endif
        values[key] = result
    }

    /// All callers share one read. Cancelling a view doesn't cancel other readers.
    /// Invalidation cancels the flight and its identity prevents late writes.
    func refresh(_ key: Key, retry: Bool = false, load: @escaping @MainActor () async throws -> RecordingNotesResult?) async throws -> RecordingNotesResult? {
        guard try acceptRevision(key) else { throw CompanionFailure.sourceUnavailable }
        if let flight = flights[key] {
            let result = try await flight.task.value
            if !retry || result?.state == "ready" { return result }
            // An explicit retry must not disappear behind a concurrent library read.
            if flights[key]?.id == flight.id { flights[key] = nil }
            return try await refresh(key, load: load)
        }
        let id = UUID()
        let task = Task { @MainActor in
            let result = try await load()
            try Task.checkCancellation()
            guard self.flights[key]?.id == id else { throw CancellationError() }
            if let result, self.valid(result, for: key) {
                try self.store(result, for: key)
            } else if result == nil || result?.state == "outdated" || result?.revision != key.revision {
                try self.removeSource(key)
            }
            return result
        }
        flights[key] = Flight(id: id, task: task)
        defer { if flights[key]?.id == id { flights[key] = nil } }
        return try await task.value
    }

    private func removeSource(_ key: Key) throws {
        values = values.filter { $0.key.owner != key.owner || $0.key.sessionID != key.sessionID }
        let url = sourceDirectory(key)
        if FileManager.default.fileExists(atPath: url.path) { try FileManager.default.removeItem(at: url) }
    }

    func invalidate(owner: String, sessionID: String) throws {
        for (key, flight) in flights where key.owner == owner && key.sessionID == sessionID {
            flight.task.cancel(); flights[key] = nil
        }
        try removeSource(Key(owner: owner, sessionID: sessionID, revision: 0))
    }

    func clear(owner: String) throws {
        for (key, flight) in flights where key.owner == owner { flight.task.cancel(); flights[key] = nil }
        values = values.filter { $0.key.owner != owner }
        let url = ownerDirectory(owner)
        if FileManager.default.fileExists(atPath: url.path) { try FileManager.default.removeItem(at: url) }
    }

    func clearAll() throws {
        flights.values.forEach { $0.task.cancel() }; flights.removeAll(); values.removeAll()
        if FileManager.default.fileExists(atPath: directory.path) { try FileManager.default.removeItem(at: directory) }
    }
}
