#if os(iOS)
import UIKit
#endif

/// A short completion allowance after audio stops, not a mechanism for keeping idle capture alive.
@MainActor
final class RecordingFinalizationTask {
    #if os(iOS)
    private var identifier: UIBackgroundTaskIdentifier = .invalid
    #endif

    func begin(onExpiration: @escaping @MainActor () -> Void) {
        #if os(iOS)
        guard identifier == .invalid else { return }
        identifier = UIApplication.shared.beginBackgroundTask(withName: "Finish recording") { [weak self] in
            onExpiration()
            self?.end()
        }
        #endif
    }

    func end() {
        #if os(iOS)
        guard identifier != .invalid else { return }
        UIApplication.shared.endBackgroundTask(identifier)
        identifier = .invalid
        #endif
    }
}
