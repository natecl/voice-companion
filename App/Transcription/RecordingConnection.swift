import Foundation

/// The session controller owns product state; the connection owns audio/network cleanup.
@MainActor
protocol RecordingConnection: AnyObject {
    func run(onReady: () -> Void, onFinishing: @escaping () -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws
    func stop()
    func cancel()
}
