import AVFoundation

/// Owns one converter, accessed only by the serial audio tap callback.
private final class PCMEncoder: @unchecked Sendable {
    let converter: AVAudioConverter
    let output: AVAudioFormat
    init(input: AVAudioFormat) throws {
        guard let output = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000,
                                         channels: 1, interleaved: true),
              let converter = AVAudioConverter(from: input, to: output) else {
            throw CaptureFailure.unavailable
        }
        self.output = output
        self.converter = converter
    }
    func encode(_ input: AVAudioPCMBuffer) throws -> Data {
        let capacity = AVAudioFrameCount(ceil(Double(input.frameLength) * 16000 / input.format.sampleRate)) + 32
        guard let buffer = AVAudioPCMBuffer(pcmFormat: output, frameCapacity: capacity) else {
            throw CaptureFailure.unavailable
        }
        var supplied = false
        var error: NSError?
        let result = converter.convert(to: buffer, error: &error) { _, status in
            if supplied { status.pointee = .noDataNow; return nil }
            supplied = true
            status.pointee = .haveData
            return input
        }
        if let error { throw error }
        guard result != .error, let bytes = buffer.int16ChannelData else { throw CaptureFailure.unavailable }
        return Data(bytes: bytes[0], count: Int(buffer.frameLength) * 2)
    }
}

enum CaptureFailure: LocalizedError {
    case unavailable, overflow, noRelay, connectionEnded
    var errorDescription: String? {
        switch self {
        case .unavailable: "The microphone audio format is unavailable."
        case .overflow: "Audio could not be sent quickly enough. Recording stopped to avoid missing speech."
        case .noRelay: "Start the development relay and launch the app with its configuration."
        case .connectionEnded: "The transcription connection ended before completion."
        }
    }
}

@MainActor
final class MicrophoneCapture {
    private let engine = AVAudioEngine()
    private var continuation: AsyncThrowingStream<Data, Error>.Continuation?
    private var hasTap = false

    func start() throws -> AsyncThrowingStream<Data, Error> {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement)
        try session.setActive(true)
        #endif
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else { throw CaptureFailure.unavailable }
        let encoder = try PCMEncoder(input: format)
        let (stream, continuation) = AsyncThrowingStream<Data, Error>.makeStream(bufferingPolicy: .bufferingOldest(50))
        self.continuation = continuation
        input.installTap(onBus: 0, bufferSize: 1600, format: format,
                         block: Self.makeTap(encoder: encoder, continuation: continuation))
        hasTap = true
        do { try engine.start() }
        catch { stop(); throw error }
        return stream
    }

    // Construct the callback outside MainActor: AVAudioEngine invokes it on its audio queue.
    nonisolated private static func makeTap(encoder: PCMEncoder,
        continuation: AsyncThrowingStream<Data, Error>.Continuation) -> AVAudioNodeTapBlock {
        { buffer, _ in
            do {
                let data = try encoder.encode(buffer)
                if !data.isEmpty, case .dropped = continuation.yield(data) {
                    continuation.finish(throwing: CaptureFailure.overflow)
                }
            } catch { continuation.finish(throwing: error) }
        }
    }

    func stop() {
        engine.stop()
        if hasTap { engine.inputNode.removeTap(onBus: 0); hasTap = false }
        continuation?.finish()
        continuation = nil
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false)
        #endif
    }
}
