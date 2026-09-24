import Foundation

struct CaptureSession: Codable, Identifiable {
    let id: UUID
    let createdAt: Date
    var transcript = Transcript()
    var completed = false
}

struct SessionStore {
    let directory: URL

    func load() throws -> [CaptureSession] {
        guard FileManager.default.fileExists(atPath: directory.path) else { return [] }
        return try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" }
            .map { try JSONDecoder().decode(CaptureSession.self, from: Data(contentsOf: $0)) }
            .sorted { $0.createdAt > $1.createdAt }
    }

    func save(_ session: CaptureSession) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try JSONEncoder().encode(session).write(to: file(session.id), options: .atomic)
    }

    func delete(_ id: UUID) throws { try FileManager.default.removeItem(at: file(id)) }
    private func file(_ id: UUID) -> URL { directory.appendingPathComponent(id.uuidString + ".json") }
}
