import AVFoundation
import Observation

@MainActor @Observable
final class MicrophoneAccess {
    enum State { case unknown, requesting, allowed, denied }
    private(set) var state: State = .unknown

    func request() async {
        guard state != .requesting else { return }
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: state = .allowed
        case .denied, .restricted: state = .denied
        case .notDetermined:
            state = .requesting
            state = await AVCaptureDevice.requestAccess(for: .audio) ? .allowed : .denied
        @unknown default: state = .denied
        }
    }
}
