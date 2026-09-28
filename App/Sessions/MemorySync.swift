import Foundation
import OSLog
import Network
import Observation

struct MemoryPassage: Codable, Equatable {
    let id: String
    let start: Double
    let duration: Double
    let text: String
    let speakers: [Int]
}

struct MemorySource: Codable, Equatable {
    let session_id: String
    var revision: Int
    let captured_at: Double
    let timezone: String
    let completed: Bool
    let origin: String?
    let passages: [MemoryPassage]

    /// A frozen Ask cutoff, including interim words; never uploaded as learned memory.
    init(live session: CaptureSession, revision: Int, finalizedOnly: Bool = false) {
        origin = nil
        session_id = session.id.uuidString
        self.revision = revision
        captured_at = session.createdAt.timeIntervalSince1970
        timezone = session.captureTimezone ?? "unknown"
        completed = false
        passages = session.transcript.segments.enumerated().compactMap { index, segment in
            guard !finalizedOnly || segment.isFinal else { return nil }
            guard !segment.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
            return MemoryPassage(id: "p\(index + 1)", start: segment.start, duration: segment.duration,
                                 text: segment.text, speakers: Array(Set(segment.words.compactMap(\.speaker))).sorted())
        }
    }

    init(_ session: CaptureSession, revision: Int) {
        origin = session.source == "personal_text" ? "personal_text" : nil
        session_id = session.id.uuidString
        self.revision = revision
        captured_at = session.createdAt.timeIntervalSince1970
        timezone = session.captureTimezone ?? "unknown"
        // Unstable partial results remain in the local transcript, never durable memory evidence.
        completed = session.completed && session.transcript.segments.allSatisfy(\.isFinal)
        passages = session.transcript.segments.enumerated().compactMap { index, segment in
            guard segment.isFinal else { return nil }
            return MemoryPassage(id: "p\(index + 1)", start: segment.start, duration: segment.duration,
                                 text: segment.text, speakers: Array(Set(segment.words.compactMap(\.speaker))).sorted())
        }
    }
}

struct MemoryOperation: Codable, Equatable {
    var version = 1
    let owner: String
    let operation: String
    var source: MemorySource?
    var session_id: String?
    var sessionID: String { source?.session_id ?? session_id! }
}

struct MemoryOutboxEntry: Codable {
    let operation: MemoryOperation
    var acknowledged: Bool
}

/// Acknowledged revisions and deletion tombstones remain durable; no automatic old-library import.
@MainActor
struct MemoryOutbox {
    let directory: URL
    let owner: String

    private func file(_ id: String) -> URL { directory.appendingPathComponent(id + ".json") }
    private func save(_ entry: MemoryOutboxEntry) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        #if os(iOS)
        let options: Data.WritingOptions = [.atomic, .completeFileProtectionUntilFirstUserAuthentication]
        #else
        let options: Data.WritingOptions = [.atomic]
        #endif
        try JSONEncoder().encode(entry).write(to: file(entry.operation.sessionID), options: options)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file(entry.operation.sessionID).path)
    }
    func entry(_ id: String) throws -> MemoryOutboxEntry? {
        guard FileManager.default.fileExists(atPath: file(id).path) else { return nil }
        let entry = try JSONDecoder().decode(MemoryOutboxEntry.self, from: Data(contentsOf: file(id)))
        guard entry.operation.owner == owner, entry.operation.sessionID == id else { throw MemorySyncFailure.ownerMismatch }
        return entry
    }
    func stage(_ session: CaptureSession) throws {
        guard session.memoryOwnerID == owner, session.memoryTerminal == true else { return }
        let previous = try entry(session.id.uuidString)
        guard previous?.operation.operation != "delete" else { return }
        var source = MemorySource(session, revision: previous?.operation.source?.revision ?? 1)
        if previous?.operation.source == source { return }
        if previous != nil { source.revision += 1 }
        try save(MemoryOutboxEntry(operation: MemoryOperation(version: source.origin == nil ? 1 : 2, owner: owner, operation: "upsert", source: source), acknowledged: false))
    }
    func delete(_ id: UUID) throws {
        try save(MemoryOutboxEntry(operation: MemoryOperation(owner: owner, operation: "delete", session_id: id.uuidString), acknowledged: false))
    }
    func acknowledge(_ operation: MemoryOperation) throws {
        // An old upload acknowledgment must not clear a newer revision or queued deletion.
        guard var current = try entry(operation.sessionID), current.operation == operation else { return }
        current.acknowledged = true
        try save(current)
    }
    func entries() throws -> [MemoryOutboxEntry] {
        guard FileManager.default.fileExists(atPath: directory.path) else { return [] }
        return try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .compactMap { try entry($0.deletingPathExtension().lastPathComponent) }
    }
}

enum MemorySyncFailure: Error {
    case ownerMismatch, invalidAcknowledgment, unavailable, sourceTooLarge
}

@MainActor
protocol MemoryTransport {
    func send(_ operation: MemoryOperation) async throws
}

@MainActor
struct MemorySocketTransport: MemoryTransport {
    let configuration: () throws -> RelayConfiguration
    init(configuration: @escaping () throws -> RelayConfiguration = { try RelayConfiguration.load() }) {
        self.configuration = configuration
    }
    func send(_ operation: MemoryOperation) async throws {
        let config = try configuration()
        guard config.memoryOwnerID == operation.owner else { throw MemorySyncFailure.ownerMismatch }
        var parts = URLComponents(url: config.url, resolvingAgainstBaseURL: false)!
        parts.path = "/memory"
        var request = URLRequest(url: parts.url!)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        let data = try JSONEncoder().encode(operation)
        guard data.count <= 63000 else { throw MemorySyncFailure.sourceTooLarge }
        let session = try config.makeSession()
        let socket = session.webSocketTask(with: request)
        defer { socket.cancel(); session.invalidateAndCancel() }
        let deadline = Task {
            try? await Task.sleep(for: .seconds(10))
            if !Task.isCancelled { socket.cancel() }
        }
        defer { deadline.cancel() }
        socket.resume()
        try await socket.send(.string(String(decoding: data, as: UTF8.self)))
        let response = try await socket.receive()
        let bytes: Data
        switch response {
        case .string(let value): bytes = Data(value.utf8)
        case .data(let value): bytes = value
        @unknown default: throw MemorySyncFailure.invalidAcknowledgment
        }
        struct Ack: Decodable {
            let type: String
            let version: Int?
            let owner: String?
            let status: String?
            let revision: Int?
        }
        let ack = try JSONDecoder().decode(Ack.self, from: bytes)
        guard ack.type == "memory_ack", ack.version == operation.version, ack.owner == operation.owner else {
            throw MemorySyncFailure.invalidAcknowledgment
        }
        if operation.operation == "delete" {
            guard ack.status == "deleted" else { throw MemorySyncFailure.invalidAcknowledgment }
        } else {
            guard ["stored", "unchanged"].contains(ack.status ?? ""), ack.revision == operation.source?.revision else {
                // Stale/deleted remote state requires diagnosis, not a false success or blind retry.
                throw MemorySyncFailure.invalidAcknowledgment
            }
        }
    }
}

@MainActor @Observable
final class MemorySync {
    let outbox: MemoryOutbox
    private let transport: any MemoryTransport
    private var task: Task<Void, Never>?
    @ObservationIgnored private var monitor: NWPathMonitor?
    private(set) var acknowledgmentCount = 0
    private(set) var lastError: String?
    private let logger = Logger(subsystem: "ai.voicecompanion.app", category: "memory")
    init(outbox: MemoryOutbox, transport: any MemoryTransport) { self.outbox = outbox; self.transport = transport }

    func stage(_ session: CaptureSession) {
        do { try outbox.stage(session); kick() }
        catch { record(error) }
    }
    func recover(store: SessionStore, activeSessionID: UUID? = nil) throws {
        // Complete interrupted tracked sessions only; legacy sessions have no owner marker.
        let deleted = Set(try outbox.entries().filter { $0.operation.operation == "delete" }.map { $0.operation.sessionID })
        for sourceID in deleted { try store.removeAnswers(referencing: sourceID) }
        for var session in try store.load() {
            guard session.id != activeSessionID else { continue }
            if deleted.contains(session.id.uuidString) {
                try store.delete(session.id)
            } else if session.memoryOwnerID == outbox.owner {
                if session.memoryTerminal != true {
                    session.memoryTerminal = true
                    session.completed = false
                    session.endReason = "Recording was interrupted before completion. Received text is saved."
                    try store.save(session)
                }
                try outbox.stage(session)
            }
        }
        kick()
    }
    func observeNetwork() {
        guard monitor == nil else { return }
        let monitor = NWPathMonitor()
        monitor.pathUpdateHandler = { [weak self] path in
            guard path.status == .satisfied else { return }
            Task { @MainActor [weak self] in self?.kick() }
        }
        monitor.start(queue: DispatchQueue(label: "ai.voicecompanion.memory-network"))
        self.monitor = monitor
    }
    deinit { monitor?.cancel() }

    func kick() {
        guard task == nil else { return }
        task = Task {
            defer { task = nil }
            do {
                // Bounded replay on foreground/finalization, no timer or retry loop on failure.
                for _ in 0..<32 {
                    guard let entry = try outbox.entries().first(where: { !$0.acknowledged }) else { break }
                    try Task.checkCancellation()
                    try await transport.send(entry.operation)
                    try outbox.acknowledge(entry.operation)
                    acknowledgmentCount += 1
                    lastError = nil
                    logger.info("memory_sync_acknowledged")
                }
            } catch { record(error) }
        }
    }
    private func record(_ error: Error) {
        lastError = String(describing: type(of: error))
        logger.error("memory_sync_failed: \(self.lastError ?? "unknown", privacy: .public)")
    }
}
