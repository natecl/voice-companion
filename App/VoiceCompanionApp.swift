import SwiftUI

@main
struct VoiceCompanionApp: App {
    var body: some Scene { WindowGroup { SessionsView() } }
}

struct SessionsView: View {
    @State private var controller = SessionController()
    @State private var microphone = MicrophoneAccess()
    @State private var microphoneCheck: String?
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Label("Voice Companion", systemImage: "waveform").font(.title.bold())
                Text(controller.current == nil ? "Ready to record" : controller.current?.source == "microphone" ? "Microphone session" : "Sample replay · microphone off").foregroundStyle(.secondary)
                if ProcessInfo.processInfo.arguments.contains("--request-microphone") {
                    Text(microphone.state == .allowed ? "Microphone permission granted. Recording has not started." :
                         microphone.state == .denied ? "Microphone access is denied. Enable it in System Settings to record." :
                         "Waiting for microphone permission…")
                        .accessibilityIdentifier("microphonePermission")
                }
                if let microphoneCheck { Text(microphoneCheck).accessibilityIdentifier("microphoneCheck") }
                if let error = controller.errorMessage {
                    Text(error).foregroundStyle(.red).accessibilityIdentifier("sessionError")
                }
                if let session = controller.current {
                    if let reason = session.endReason, reason != controller.errorMessage { Text(reason).foregroundStyle(.secondary) }
                    Text(controller.liveStatus ?? (controller.isReplaying ? "Replaying sample…" : (session.completed ? "Saved" : "Incomplete · saved")))
                        .accessibilityIdentifier("sessionStatus")
                    if session.transcript.segments.isEmpty {
                        Text(controller.isActive ? "Waiting for transcript…" : "No transcript was received.")
                    }
                    ForEach(session.transcript.segments) { segment in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(String(format: "%.1fs", segment.start)).font(.caption).foregroundStyle(.secondary)
                            if segment.words.isEmpty {
                                Text("Speaker pending").font(.caption)
                                Text(segment.text)
                            } else {
                                // Keep word attribution visible without changing provider output.
                                Text(attributedWords(segment.words))
                            }
                        }
                        .accessibilityElement(children: .contain)
                        .accessibilityIdentifier("transcriptSegment")
                    }
                    if controller.liveStatus != nil {
                        Button("Stop recording") { controller.stop() }
                            .disabled(controller.liveStatus == "Finishing…")
                            .accessibilityIdentifier("stopRecording")
                    } else if controller.isReplaying {
                        Button("Stop replay") { controller.stop() }.accessibilityIdentifier("stopReplay")
                    } else {
                        Button("Delete session", role: .destructive) { controller.deleteCurrent() }
                            .accessibilityIdentifier("deleteSession")
                    }
                    Button("Back to sessions") { controller.close() }.disabled(controller.liveStatus != nil).accessibilityIdentifier("closeSession")
                } else {
                    Button("Start recording") { controller.startRecording() }
                        .disabled(controller.isActive).accessibilityIdentifier("startRecording")
                    if let status = controller.liveStatus {
                        Text(status)
                        Button("Stop recording") { controller.stop() }.accessibilityIdentifier("stopRecording")
                    }
                    Button("Replay sample") { controller.startReplay() }
                        .buttonStyle(.borderedProminent).disabled(controller.isActive).accessibilityIdentifier("replaySample")
                    if controller.sessions.isEmpty { Text("No saved sessions yet.") }
                    ForEach(controller.sessions) { session in
                        Button {
                            controller.current = session
                        } label: {
                            VStack(alignment: .leading) {
                                Text(session.source == "microphone" ? "Recorded conversation" : "Sample conversation")
                                Text(session.createdAt.formatted()).font(.caption)
                            }
                        }.accessibilityIdentifier("savedSession")
                    }
                }
            }.accessibilityElement(children: .contain).padding(24).frame(maxWidth: .infinity, alignment: .leading)
        }
        .task {
            if ProcessInfo.processInfo.arguments.contains("--relay-check") {
                microphoneCheck = "Checking encrypted relay connection…"
                do {
                    let config = try RelayConfiguration.load()
                    let session = try config.makeSession()
                    defer { session.invalidateAndCancel() }
                    var components = URLComponents(url: config.url, resolvingAgainstBaseURL: false)!
                    components.scheme = config.url.scheme == "wss" ? "https" : "http"
                    components.path = "/health"
                    let (_, response) = try await session.data(from: components.url!)
                    guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw CaptureFailure.connectionEnded }
                    microphoneCheck = "Relay connection verified. No microphone capture or provider call."
                } catch { microphoneCheck = "Relay check failed: \(error.localizedDescription)" }
            }
            if ProcessInfo.processInfo.arguments.contains("--microphone-check") || ProcessInfo.processInfo.arguments.contains("--microphone-interruption-check") {
                microphoneCheck = "Checking microphone locally…"
                do {
                    let capture = MicrophoneCapture()
                    let stream = try capture.start()
                    let duration = ProcessInfo.processInfo.arguments.contains("--microphone-interruption-check") ? 120 : 5
                    let stopTask = Task { try? await Task.sleep(for: .seconds(duration)); capture.stop() }
                    defer { stopTask.cancel(); capture.stop() }
                    var bytes = 0
                    var peak = 0
                    for try await frame in stream {
                        bytes += frame.count
                        frame.withUnsafeBytes { raw in
                            for sample in raw.bindMemory(to: Int16.self) { peak = max(peak, abs(Int(sample))) }
                        }
                    }
                    microphoneCheck = "Local microphone check: \(bytes) PCM bytes; peak \(peak). Capture stopped. No upload."
                } catch { microphoneCheck = "Microphone check failed: \(error.localizedDescription)" }
            }
            if ProcessInfo.processInfo.arguments.contains("--request-microphone") {
                await microphone.request()
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background && controller.isActive {
                controller.interrupt(reason: "Recording stopped because the app left the foreground. Received text is saved; the transcript may be incomplete.")
            }
        }
    }

    private func attributedWords(_ words: [TranscriptWord]) -> String {
        var result = ""
        var previous: Int? = nil
        for (index, word) in words.enumerated() {
            if index == 0 || previous != word.speaker {
                let label = word.speaker.map { "Speaker \($0 + 1)" } ?? "Speaker pending"
                result += (index == 0 ? "" : "\n\n") + label + "\n"
            } else { result += " " }
            result += word.text
            previous = word.speaker
        }
        return result
    }
}
