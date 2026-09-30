import Foundation

struct CaptureSession: Codable, Identifiable {
    let id: UUID
    let createdAt: Date
    var transcript = Transcript()
    var completed = false
    var source: String? = nil
    var endReason: String? = nil
    var stopNotice: String? = nil
    var recordingSeconds: Double? = nil
    var answers: [ConversationAnswer]? = nil
    var memoryOwnerID: String? = nil
    var memoryTerminal: Bool? = nil
    var captureTimezone: String? = nil
}

struct SessionStore {
    let directory: URL
    var expectedOwner: String? = nil

    func load() throws -> [CaptureSession] {
        guard FileManager.default.fileExists(atPath: directory.path) else { return [] }
        return try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" }
            .map {
                var session = try JSONDecoder().decode(CaptureSession.self, from: Data(contentsOf: $0))
                if let expectedOwner, session.memoryOwnerID != expectedOwner { throw AccountFailure.signInRequired }
                session.answers = session.answers?.map { item in
                    var answer = item
                    if answer.state == .streaming {
                        answer.state = .failed
                        answer.notice = "This answer was interrupted before completion. Partial text is saved."
                    }
                    return answer
                }
                return session
            }
            .sorted { $0.createdAt > $1.createdAt }
    }

    func save(_ session: CaptureSession) throws {
        if expectedOwner != nil, FileManager.default.fileExists(atPath: directory.deletingLastPathComponent().appendingPathComponent(LocalAccountErasure.marker).path) {
            throw AccountFailure.signInRequired
        }
        if let expectedOwner, session.memoryOwnerID != expectedOwner { throw AccountFailure.signInRequired }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        #if os(iOS)
        // Sessions must remain writable after locking a device that has already been unlocked.
        let options: Data.WritingOptions = [.atomic, .completeFileProtectionUntilFirstUserAuthentication]
        #else
        let options: Data.WritingOptions = .atomic
        #endif
        try JSONEncoder().encode(session).write(to: file(session.id), options: options)
    }

    func removeAnswers(referencing sourceID: String) throws {
        for var session in try load() {
            let retained = session.answers?.filter { answer in
                !(answer.pastSources ?? []).contains { $0.session_id == sourceID }
            }
            if retained?.count != session.answers?.count {
                session.answers = retained
                try save(session)
            }
        }
    }
    func delete(_ id: UUID) throws {
        try removeAnswers(referencing: id.uuidString)
        try FileManager.default.removeItem(at: file(id))
    }
    private func file(_ id: UUID) -> URL { directory.appendingPathComponent(id.uuidString + ".json") }
}
