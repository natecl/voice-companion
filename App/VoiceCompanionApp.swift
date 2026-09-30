import SwiftUI
import AVFoundation

@main
struct VoiceCompanionApp: App {
    private let companionEnabled: Bool
    private let sharedRoomEnabled: Bool
    init() {
        let arguments = ProcessInfo.processInfo.arguments
        var key = "companionEnabled"
        if arguments.contains("--ui-testing") {
            // Isolate test activation from the installed user's preference and other fixtures.
            let raw = ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"] ?? ""
            let owner = (try? JSONDecoder().decode(RelayConfiguration.self, from: Data(raw.utf8)))?.memoryOwnerID
            key = "companion-ui-qa-" + (owner ?? UUID().uuidString)
        }
        if arguments.contains("--enable-companion-ui") { UserDefaults.standard.set(true, forKey: key) }
        if arguments.contains("--disable-companion-ui") { UserDefaults.standard.set(false, forKey: key) }
        companionEnabled = arguments.contains("--companion-ui") || UserDefaults.standard.bool(forKey: key)
        let roomKey = key + "-shared-room"
        if arguments.contains("--shared-room-ui") { UserDefaults.standard.set(true, forKey: roomKey) }
        if arguments.contains("--disable-shared-room-ui") { UserDefaults.standard.set(false, forKey: roomKey) }
        sharedRoomEnabled = UserDefaults.standard.bool(forKey: roomKey)
    }
    var body: some Scene {
        WindowGroup {
            #if DEBUG && os(iOS)
            if ProcessInfo.processInfo.arguments.contains("--account-keychain-fixture") {
                AccountDeletionKeychainFixture()
            } else if ProcessInfo.processInfo.arguments.contains("--account-deletion-ui-fixture") {
                AccountDeletionUIFixture()
            } else { accountContent }
            #else
            accountContent
            #endif
        }
    }
    @ViewBuilder private var accountContent: some View {
        if ProcessInfo.processInfo.arguments.contains("--ui-testing") {
            appContent(authenticated: false)
        } else { AccountRootView { appContent(authenticated: $0) } }
    }
    @ViewBuilder private func appContent(authenticated: Bool) -> some View {
        if companionEnabled || authenticated {
            #if os(iOS)
            if sharedRoomEnabled || authenticated { SharedRoomRootView() }
            else { CompanionRootView() }
            #else
            CompanionRootView()
            #endif
        } else { SessionsView() }
    }
}

struct SessionsView: View {
    @State private var controller = SessionController.forApp()
    @State private var writingPersonalNote = false
    @State private var personalDraft = ""
    @State private var confirmingDeletion = false
    @State private var microphone = MicrophoneAccess()
    @State private var microphoneCheck: String?
    @Environment(\.scenePhase) private var scenePhase

    private var isMicrophoneCheck: Bool {
        let arguments = ProcessInfo.processInfo.arguments
        return arguments.contains("--microphone-check") || arguments.contains("--microphone-interruption-check")
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Label("Voice Companion", systemImage: "waveform").font(.title.bold())
                    Text(isMicrophoneCheck ? "Local microphone diagnostic · no upload" : controller.current == nil ? "Ready to record" : controller.current?.source == "personal_text" ? "Personal note" : controller.current?.source == "microphone" ? "Microphone session" : "Sample replay · microphone off").foregroundStyle(.secondary)
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
                    if isMicrophoneCheck {
                        Text("Capture starts automatically. Normal recording controls are unavailable during this diagnostic.")
                    } else if let session = controller.current {
                        if session.source == "microphone", controller.liveStatus != nil || session.recordingSeconds != nil {
                            TimelineView(.periodic(from: .now, by: 1)) { _ in
                                let seconds = Int(controller.elapsedRecordingSeconds)
                                Text(String(format: "%d:%02d elapsed", seconds / 60, seconds % 60))
                                    .monospacedDigit().accessibilityIdentifier("recordingElapsed")
                            }
                            if controller.liveStatus != nil { recordingLimitNotice }
                        }
                        if let notice = session.stopNotice {
                            Text(notice).foregroundStyle(.secondary).accessibilityIdentifier("stopNotice")
                        }
                        if let reason = session.endReason, reason != controller.errorMessage { Text(reason).foregroundStyle(.secondary) }
                        Text(controller.liveStatus ?? (controller.isReplaying ? "Replaying sample…" : (session.completed ? "Saved" : "Incomplete · saved")))
                            .accessibilityIdentifier("sessionStatus")
                        if let status = controller.personalNoteSyncStatus {
                            Text(status).font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("personalSyncStatus")
                        }
                        if session.transcript.segments.isEmpty {
                            Text(controller.isActive ? "Waiting for transcript…" : "No transcript was received.")
                        }
                        if !controller.isReplaying, !session.transcript.segments.isEmpty {
                            ConversationAskView(controller: controller, answers: session.answers ?? []).id(session.id)
                        }
                        ForEach(session.transcript.segments) { segment in
                            VStack(alignment: .leading, spacing: 8) {
                                if session.source != "personal_text" {
                                    Text(String(format: "%.1fs", segment.start)).font(.caption).foregroundStyle(.secondary)
                                }
                                if segment.words.isEmpty {
                                    if session.source != "personal_text" { Text("Speaker pending").font(.caption) }
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
                        } else if controller.liveStatus == nil {
                            Button("Delete session", role: .destructive) { confirmingDeletion = true }
                                .disabled(controller.isAnswering).accessibilityIdentifier("deleteSession")
                        }
                        Button("Back to sessions") { controller.close() }.disabled(controller.liveStatus != nil || controller.isAnswering).accessibilityIdentifier("closeSession")
                    } else {
                        recordingLimitNotice
                        #if os(iOS)
                        Text("After recording starts, you can lock your phone. Reopen the app to stop. Calls or microphone changes may end the recording.")
                            .font(.caption).foregroundStyle(.secondary)
                        #endif
                        Button("Start recording") { controller.startRecording() }
                            .disabled(controller.isActive).accessibilityIdentifier("startRecording")
                        if let status = controller.liveStatus {
                            Text(status)
                        }
                        Button("Replay sample") { controller.startReplay() }
                            .buttonStyle(.borderedProminent).disabled(controller.isActive).accessibilityIdentifier("replaySample")
                        if controller.canSavePersonalNote {
                            Button("Add personal note") { writingPersonalNote = true }
                                .accessibilityIdentifier("addPersonalNote")
                        }
                        if controller.sessions.isEmpty { Text("No saved sessions yet.") }
                        ForEach(controller.sessions) { session in
                            Button {
                                controller.current = session
                            } label: {
                                VStack(alignment: .leading) {
                                    Text(session.source == "personal_text" ? "Personal note" : session.source == "microphone" ? "Recorded conversation" : "Sample conversation")
                                    Text(session.createdAt.formatted()).font(.caption)
                                }
                            }.accessibilityIdentifier("savedSession")
                        }
                    }
                }.accessibilityElement(children: .contain).padding(24).frame(maxWidth: .infinity, alignment: .leading)
            }
            if let status = controller.liveStatus {
                HStack {
                    Text(status)
                    Spacer()
                    Button("Stop recording") { controller.stop() }
                        .disabled(status == "Finishing…" || status == "Stopping…")
                        .accessibilityIdentifier("stopRecording")
                }
                .padding().background(.regularMaterial)
            }
        }
        .sheet(isPresented: $writingPersonalNote) {
            VStack(alignment: .leading, spacing: 16) {
                Text("Personal note").font(.title2.bold())
                Text("Share something about your life. This is saved as a note written by you; people you mention remain separate.")
                TextEditor(text: $personalDraft).frame(minHeight: 160).accessibilityIdentifier("personalNoteText")
                if let error = controller.errorMessage { Text(error).foregroundStyle(.red) }
                HStack {
                    Button("Cancel") { writingPersonalNote = false }
                    Spacer()
                    Button("Save note") {
                        if controller.savePersonalNote(personalDraft) {
                            personalDraft = ""
                            writingPersonalNote = false
                        }
                    }.disabled(personalDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .accessibilityIdentifier("savePersonalNote")
                }
            }.padding(24).frame(minWidth: 300)
        }
        .alert("Delete this session?", isPresented: $confirmingDeletion) {
            Button("Cancel", role: .cancel) {}
            Button("Delete", role: .destructive) { controller.deleteCurrent() }
                .accessibilityIdentifier("confirmDeleteSession")
        } message: {
            Text(controller.current?.source == "personal_text"
                 ? "This permanently deletes the saved note and its questions and answers. This cannot be undone."
                 : "This deletes the transcript and its questions and answers. Learned memories and their supporting excerpts may remain with your companion.")
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
            if isMicrophoneCheck {
                microphoneCheck = "Starting local capture…"
                var bytes = 0
                var peak = 0
                var inputDescription = "system-selected microphone"
                do {
                    let capture = MicrophoneCapture()
                    let stream = try capture.start()
                    #if os(iOS)
                    inputDescription = AVAudioSession.sharedInstance().currentRoute.inputs
                        .map { "\($0.portName) [\($0.portType.rawValue)]" }.joined(separator: ", ")
                    #endif
                    microphoneCheck = "Capturing locally from \(inputDescription). No upload."
                    let duration = ProcessInfo.processInfo.arguments.contains("--microphone-interruption-check") ? 120 : 5
                    let stopTask = Task { try? await Task.sleep(for: .seconds(duration)); capture.stop() }
                    defer { stopTask.cancel(); capture.stop() }
                    for try await frame in stream {
                        bytes += frame.count
                        frame.withUnsafeBytes { raw in
                            for sample in raw.bindMemory(to: Int16.self) { peak = max(peak, abs(Int(sample))) }
                        }
                    }
                    microphoneCheck = "Local microphone check: \(bytes) PCM bytes; peak \(peak). Capture stopped. No upload."
                } catch {
                    let reason = (error as? CaptureFailure) == .interrupted
                        ? "Audio capture was interrupted or its input changed."
                        : error.localizedDescription
                    microphoneCheck = "Local capture stopped: \(reason) Input: \(inputDescription); \(bytes) PCM bytes; peak \(peak). No upload."
                }
            }
            if ProcessInfo.processInfo.arguments.contains("--request-microphone") {
                await microphone.request()
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { controller.didEnterBackground() }
            if phase == .active { controller.didBecomeActive() }
        }
    }

    private var recordingLimitNotice: some View {
        Text("Development build · recordings stop automatically after \(controller.recordingLimit.components.seconds) seconds.")
            .font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("recordingLimit")
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
