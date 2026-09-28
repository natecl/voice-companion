import AVFoundation
import Speech

struct DictationEvent: Sendable {
    let text: String
    let isFinal: Bool
}

enum DictationFailure: LocalizedError {
    case permission, unavailable, interrupted, timeout
    var errorDescription: String? {
        switch self {
        case .permission: "Dictation needs microphone and speech recognition access. You can enable them in Settings."
        case .unavailable: "On-device dictation is unavailable for this language right now. You can still type your message."
        case .interrupted: "Dictation was interrupted. Review the captured text before sending."
        case .timeout: "Dictation could not finish. Review the captured text before sending."
        }
    }
}

@MainActor
protocol DictationRecognizing: AnyObject {
    var audioLevel: Double { get }
    func start() async throws -> AsyncThrowingStream<DictationEvent, Error>
    func finish()
    func cancel()
}

extension DictationRecognizing { var audioLevel: Double { 0 } }

/// Composer-only speech recognition. No relay calls, saved sessions, or automatic cloud fallback.
@MainActor
final class AppleDictationRecognizer: DictationRecognizing {
    private(set) var audioLevel: Double = 0
    private let capture: any AudioCapture
    private var recognizer: SFSpeechRecognizer?
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var recognition: SFSpeechRecognitionTask?
    private var audioTask: Task<Void, Never>?
    private var continuation: AsyncThrowingStream<DictationEvent, Error>.Continuation?

    init(capture: any AudioCapture = SharedMicrophoneCapture(purpose: .dictation)) { self.capture = capture }

    func start() async throws -> AsyncThrowingStream<DictationEvent, Error> {
        let microphone = MicrophoneAccess()
        await microphone.request()
        try Task.checkCancellation()
        guard microphone.state == .allowed else { throw DictationFailure.permission }
        let permission = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization(Self.authorizationHandler(continuation))
        }
        try Task.checkCancellation()
        guard permission == .authorized else { throw DictationFailure.permission }
        guard let recognizer = SFSpeechRecognizer(locale: .current), recognizer.isAvailable,
              recognizer.supportsOnDeviceRecognition else { throw DictationFailure.unavailable }
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.requiresOnDeviceRecognition = true
        request.shouldReportPartialResults = true
        request.taskHint = .dictation
        request.addsPunctuation = true
        let (stream, continuation) = AsyncThrowingStream<DictationEvent, Error>.makeStream(bufferingPolicy: .bufferingNewest(1))
        self.recognizer = recognizer; self.request = request; self.continuation = continuation
        recognition = recognizer.recognitionTask(with: request, resultHandler: Self.resultHandler(continuation))
        do {
            let audio = try capture.start()
            audioTask = Task {
                do {
                    for try await frame in audio {
                        try Task.checkCancellation()
                        guard let format = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true),
                              frame.count % 2 == 0,
                              let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frame.count / 2)),
                              let samples = buffer.int16ChannelData else { throw DictationFailure.unavailable }
                        buffer.frameLength = buffer.frameCapacity
                        frame.copyBytes(to: UnsafeMutableRawBufferPointer(start: samples[0], count: frame.count))
                        audioLevel = Self.level(samples: samples[0], count: Int(buffer.frameLength))
                        request.append(buffer)
                    }
                    request.endAudio()
                } catch {
                    if !Task.isCancelled { continuation.finish(throwing: DictationFailure.interrupted) }
                }
            }
        } catch { cancel(); throw error }
        return stream
    }

    // Speech invokes callbacks on framework-owned queues. Construct them outside
    // MainActor isolation; continuations safely deliver values to the consumer.
    nonisolated static func authorizationHandler(
        _ continuation: CheckedContinuation<SFSpeechRecognizerAuthorizationStatus, Never>
    ) -> @Sendable (SFSpeechRecognizerAuthorizationStatus) -> Void {
        { status in continuation.resume(returning: status) }
    }

    nonisolated static func resultHandler(
        _ continuation: AsyncThrowingStream<DictationEvent, Error>.Continuation
    ) -> @Sendable (SFSpeechRecognitionResult?, Error?) -> Void {
        { result, error in
            if let result {
                continuation.yield(DictationEvent(text: result.bestTranscription.formattedString, isFinal: result.isFinal))
                if result.isFinal { continuation.finish(); return }
            }
            if error != nil { continuation.finish(throwing: DictationFailure.interrupted) }
        }
    }

    /// RMS from the same PCM frames sent to recognition; no second microphone consumer.
    nonisolated static func level(samples: UnsafePointer<Int16>, count: Int) -> Double {
        guard count > 0 else { return 0 }
        var energy = 0.0
        for i in 0..<count { let sample = Double(samples[i]) / 32768; energy += sample * sample }
        let rms = sqrt(energy / Double(count))
        return min(1, max(0, (20 * log10(max(rms, 0.00001)) + 50) / 50))
    }

    func finish() { audioLevel = 0; capture.stop() } // Drain already captured frames before endAudio.
    func cancel() {
        audioLevel = 0
        capture.stop(); audioTask?.cancel(); audioTask = nil
        recognition?.cancel(); recognition = nil
        continuation?.finish(); continuation = nil
        request = nil; recognizer = nil
    }
}
