import Foundation

@MainActor
protocol AudioCapture: AnyObject {
    func start() throws -> AsyncThrowingStream<Data, Error>
    func stop()
}
