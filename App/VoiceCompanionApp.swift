import SwiftUI
import OSLog

@main
struct VoiceCompanionApp: App {
    var body: some Scene {
        WindowGroup {
            FoundationView()
        }
    }
}

struct FoundationView: View {
    @State private var showingSession = false
    private let logger = Logger(subsystem: "ai.voicecompanion.app", category: "navigation")

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Label("Voice Companion", systemImage: "waveform")
                .font(.largeTitle.bold())
            if showingSession {
                Text("Your transcript will appear here.")
                    .accessibilityIdentifier("transcriptPlaceholder")
                Text("Recording is not available in this foundation build.")
                    .foregroundStyle(.secondary)
                Button("Back to sessions") {
                    showingSession = false
                    logger.info("session_closed")
                }
                .accessibilityIdentifier("closeSession")
            } else {
                Text("Your conversations, captured.")
                    .font(.title2)
                Text("No saved sessions yet.")
                    .foregroundStyle(.secondary)
                Button("New session") {
                    showingSession = true
                    logger.info("session_opened")
                }
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("newSession")
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .onAppear { logger.info("foundation_ready") }
    }
}
