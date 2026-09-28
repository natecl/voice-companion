import XCTest

@MainActor
private final class ProactiveFixture: ProactiveConnection {
    var observed: [MemorySource] = []
    var quietCalls = 0
    var cancelled = false
    var events: [ProactiveEvent] = []
    func run(capture: String, onEvent: (ProactiveEvent) throws -> Void) async throws {
        try onEvent(ProactiveEvent(type: "ready", enabled: true, turn_id: nil))
        while !cancelled {
            try Task.checkCancellation()
            while !events.isEmpty { try onEvent(events.removeFirst()) }
            try await Task.sleep(for: .milliseconds(2))
        }
    }
    func observe(_ source: MemorySource) async throws { observed.append(source) }
    func quiet(capture: String) async throws { quietCalls += 1 }
    func cancel() { cancelled = true }
}

@MainActor
final class ProactiveCoordinatorTests: XCTestCase {
    private func capture() -> CaptureSession {
        var value = CaptureSession(id: UUID(), createdAt: Date())
        value.transcript.segments = [TranscriptSegment(start: 0, duration: 2, text: "Stable words", words: [], isFinal: true),
            TranscriptSegment(start: 3, duration: 2, text: "Interim words", words: [], isFinal: false)]
        return value
    }
    private func settle() async throws { try await Task.sleep(for: .milliseconds(35)) }
    func testFinalizedOnlyAndQuietRejectsAlreadyQueuedMessage() async throws {
        let socket = ProactiveFixture(); var delivered = 0
        let coordinator = ProactiveCoordinator(makeConnection: { socket }, received: { delivered += 1 })
        let source = MemorySource(live: capture(), revision: 1, finalizedOnly: true)
        XCTAssertEqual(source.passages.map(\.text), ["Stable words"])
        coordinator.update(source, foreground: true); try await settle()
        XCTAssertEqual(socket.observed.count, 1)
        coordinator.quiet()
        socket.events.append(ProactiveEvent(type: "contribution", enabled: nil, turn_id: "late"))
        try await settle()
        XCTAssertEqual(socket.quietCalls, 1); XCTAssertEqual(delivered, 0)
        XCTAssertNil(coordinator.latestMessageID)
        coordinator.suspend()
    }
    func testForegroundRequiresNewTextAndCaptureReset() async throws {
        var sockets: [ProactiveFixture] = []; var delivered = 0
        let coordinator = ProactiveCoordinator(makeConnection: { let s = ProactiveFixture(); sockets.append(s); return s }, received: { delivered += 1 })
        var session = capture()
        let initial = MemorySource(live: session, revision: 1, finalizedOnly: true)
        coordinator.update(initial, foreground: true); try await settle()
        sockets[0].events.append(ProactiveEvent(type: "contribution", enabled: nil, turn_id: "first"))
        try await settle(); XCTAssertEqual(delivered, 1)
        coordinator.update(initial, foreground: false)
        coordinator.update(initial, foreground: true); try await settle()
        XCTAssertEqual(sockets.count, 1); XCTAssertTrue(sockets[0].cancelled)
        session.transcript.segments[1] = TranscriptSegment(start: 3, duration: 2, text: "Final words", words: [], isFinal: true)
        coordinator.update(MemorySource(live: session, revision: 1, finalizedOnly: true), foreground: true)
        try await settle(); XCTAssertEqual(sockets.count, 2)
        XCTAssertEqual(sockets[1].observed.first?.revision, 2)
        coordinator.quiet(); coordinator.update(nil, foreground: true)
        coordinator.update(MemorySource(live: capture(), revision: 1, finalizedOnly: true), foreground: true)
        try await settle(); XCTAssertFalse(coordinator.isQuiet); XCTAssertEqual(sockets.count, 3)
        coordinator.suspend()
    }
}
