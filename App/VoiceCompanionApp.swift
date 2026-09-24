import SwiftUI

@main
struct VoiceCompanionApp: App {
    var body: some Scene { WindowGroup { SessionsView() } }
}

struct SessionsView: View {
    @State private var controller = SessionController()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Label("Voice Companion", systemImage: "waveform").font(.title.bold())
                Text("Sample replay · microphone off").foregroundStyle(.secondary)
                if let error = controller.errorMessage {
                    Text(error).foregroundStyle(.red).accessibilityIdentifier("sessionError")
                }
                if let session = controller.current {
                    Text(controller.isReplaying ? "Replaying sample…" : (session.completed ? "Saved" : "Incomplete · saved"))
                        .accessibilityIdentifier("sessionStatus")
                    if session.transcript.segments.isEmpty { Text("Waiting for transcript…") }
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
                    if controller.isReplaying {
                        Button("Stop replay") { controller.stop() }.accessibilityIdentifier("stopReplay")
                    } else {
                        Button("Delete session", role: .destructive) { controller.deleteCurrent() }
                            .accessibilityIdentifier("deleteSession")
                    }
                    Button("Back to sessions") { controller.close() }.accessibilityIdentifier("closeSession")
                } else {
                    Button("Replay sample") { controller.startReplay() }
                        .buttonStyle(.borderedProminent).accessibilityIdentifier("replaySample")
                    if controller.sessions.isEmpty { Text("No saved sessions yet.") }
                    ForEach(controller.sessions) { session in
                        Button {
                            controller.current = session
                        } label: {
                            VStack(alignment: .leading) {
                                Text("Sample conversation")
                                Text(session.createdAt.formatted()).font(.caption)
                            }
                        }.accessibilityIdentifier("savedSession")
                    }
                }
            }.accessibilityElement(children: .contain).padding(24).frame(maxWidth: .infinity, alignment: .leading)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background && controller.isReplaying { controller.stop() }
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
