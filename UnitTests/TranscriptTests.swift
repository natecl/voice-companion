import XCTest

final class TranscriptTests: XCTestCase {
    func testStitchedResultReplacesChunksAndPreservesPreviousUtterance() {
        var transcript = Transcript()
        func segment(_ start: Double, _ duration: Double, _ text: String) -> TranscriptSegment {
            TranscriptSegment(start: start, duration: duration, text: text, words: [], isFinal: true)
        }
        transcript.apply(segment(0, 2, "Earlier utterance"))
        transcript.apply(segment(3, 2, "Partial"))
        transcript.apply(segment(5, 2, "Later chunk"))
        transcript.apply(segment(3, 4, "Complete utterance"))
        XCTAssertEqual(transcript.segments.map(\.text), ["Earlier utterance", "Complete utterance"])
        transcript.apply(segment(3, 4, ""))
        XCTAssertEqual(transcript.segments.count, 2)
    }

    func testRecordedProviderRevisionsDoNotDuplicateFinalWords() throws {
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Fixtures/transcript-events.json")
        let events = try JSONDecoder().decode([ReplayEvent].self, from: Data(contentsOf: fixture))
        var transcript = Transcript()
        for item in events {
            if let segment = item.event.segment { transcript.apply(segment) }
        }
        XCTAssertEqual(transcript.segments.count, 1)
        XCTAssertEqual(transcript.segments.first?.words.count, 30)
        XCTAssertEqual(Set(transcript.segments.flatMap(\.words).compactMap(\.speaker)), [0, 1])
        let completion = try JSONDecoder().decode(GrokEvent.self, from: Data(
            "{\"type\":\"transcript.done\",\"text\":\"\"}".utf8))
        XCTAssertNil(completion.segment)
    }

    func testStoreRoundTripAndDelete() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let session = CaptureSession(id: UUID(), createdAt: Date())
        try store.save(session)
        XCTAssertEqual(try store.load().first?.id, session.id)
        try store.delete(session.id)
        XCTAssertTrue(try store.load().isEmpty)
    }

    func testOlderSavedSessionLoadsWithoutRecordingMetadata() throws {
        let data = Data("""
        {"id":"11111111-1111-1111-1111-111111111111","createdAt":0,
         "transcript":{"segments":[]},"completed":true,"source":"microphone"}
        """.utf8)
        let session = try JSONDecoder().decode(CaptureSession.self, from: data)
        XCTAssertTrue(session.completed)
        XCTAssertNil(session.stopNotice)
        XCTAssertNil(session.recordingSeconds)
    }

    func testCorruptSessionIsReported() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        try Data("invalid".utf8).write(to: directory.appendingPathComponent("bad.json"))
        XCTAssertThrowsError(try SessionStore(directory: directory).load())
    }
}
