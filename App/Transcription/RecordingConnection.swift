import Foundation

/// The session controller owns product state; the connection owns audio/network cleanup.
@MainActor
protocol RecordingConnection: AnyObject {
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws
    func stop()
    func cancel()
}

enum RecordingStopReason { case user, developmentLimit }
