import SwiftUI

/// Opt-in while hosted rollout is pending. Both surfaces stay mounted to preserve reading position.
struct CompanionRootView: View {
    @State private var recording = SessionController.forApp()
    @State private var chat: CompanionController?
    @State private var dictation = ComposerDictation.forApp()
    @State private var surface = "Companion"
    @State private var selectedID: UUID?
    @State private var citedSource: CompanionEvidence?
    @State private var sourceNotice: String?
    @State private var recordingTab = "Notes"
    @State private var notePassage: MemoryPassage?
    @State private var confirmingDeletion = false
    @State private var needsChatRefresh = false
    @State private var sourceTask: Task<Void, Never>?
    @FocusState private var composing: Bool
    @Environment(\.scenePhase) private var scenePhase

    private static func config() throws -> RelayConfiguration {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--ui-testing"), ProcessInfo.processInfo.arguments.contains("--companion-ui-fixture") {
            let raw = ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"] ?? ""
            let config = try JSONDecoder().decode(RelayConfiguration.self, from: Data(raw.utf8))
            guard config.url.scheme == "ws", config.url.host == "127.0.0.1", config.memoryOwnerID != nil else { throw CaptureFailure.noRelay }
            return config
        }
        #endif
        return try RelayConfiguration.load()
    }
    private func connection(owner: String) -> CompanionSocketConnection {
        CompanionSocketConnection(configuration: {
            let config = try Self.config()
            guard config.memoryOwnerID == owner else { throw AskFailure.accessExpired }
            return config
        })
    }
    private var selected: CaptureSession? {
        if recording.current?.id == selectedID { return recording.current }
        return recording.sessions.first { $0.id == selectedID }
    }
    private var library: [CaptureSession] {
        var sessions = recording.sessions
        if let current = recording.current, recording.isActive {
            sessions.removeAll { $0.id == current.id }; sessions.insert(current, at: 0)
        }
        return sessions
    }
    var body: some View {
        VStack(spacing: 12) {
            Picker("View", selection: $surface) {
                Text("Companion").tag("Companion")
                Text("Recordings").tag("Recordings")
            }.pickerStyle(.segmented).accessibilityIdentifier("companionNavigation")
            if let error = recording.errorMessage { Text(error).foregroundStyle(.red) }
            if recording.pendingMemoryDeletion {
                Text("Deleting the source from companion memory… Chat will resume after synchronization.")
                    .font(.caption).accessibilityIdentifier("deletionPending")
            }
            ZStack {
                chatContent.opacity(surface == "Companion" ? 1 : 0)
                    .allowsHitTesting(surface == "Companion").accessibilityHidden(surface != "Companion")
                libraryContent.opacity(surface == "Recordings" ? 1 : 0)
                    .allowsHitTesting(surface == "Recordings").accessibilityHidden(surface != "Recordings")
            }
            if recording.liveStatus == "Recording", SharedMicrophone.shared.meetingAudioPaused {
                Text("Meeting audio is not being captured while you dictate. Capture resumes automatically when dictation stops.")
                    .font(.caption).accessibilityIdentifier("meetingDictationPause")
            }
            Divider()
            HStack {
                if let status = recording.liveStatus {
                    Button(status == "Recording" && SharedMicrophone.shared.meetingAudioPaused ? "Meeting capture paused for dictation" : status) { selectedID = recording.current?.id; citedSource = nil; surface = "Recordings" }
                        .accessibilityIdentifier("showActiveRecording")
                    Spacer()
                    Button("Stop recording") { recording.stop() }
                        .disabled(status != "Recording").accessibilityIdentifier("stopRecording")
                } else {
                    Button("Capture meeting note") { recording.startRecording() }
                        .accessibilityIdentifier("startRecording")
                    Spacer()
                }
            }
        }.padding().frame(minWidth: 300, minHeight: 420)
        .task {
            do {
                let config = try Self.config()
                guard let owner = config.memoryOwnerID else { throw CaptureFailure.noRelay }
                chat = CompanionController(owner: owner, makeConnection: { connection(owner: owner) })
                if !recording.pendingMemoryDeletion { chat?.refresh() }
            } catch { sourceNotice = error.localizedDescription }
        }
        .onChange(of: selected.flatMap { recording.companionAttachment(for: $0) }) { _, _ in notePassage = nil }
        .onChange(of: selectedID) { _, _ in notePassage = nil; recordingTab = citedSource == nil ? "Notes" : "Transcript" }
        .onChange(of: surface) { _, value in if value == "Recordings" { composing = false; dictation.interrupt() } }
        .onChange(of: recording.pendingMemoryDeletion) { _, pending in
            if pending { dictation.interrupt(); chat?.clearForSourceDeletion() }
            else { needsChatRefresh = true; refreshWhenReady() }
        }
        .onChange(of: chat?.isBusy) { _, _ in refreshWhenReady() }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background {
                dictation.interrupt(); recording.didEnterBackground(); chat?.didEnterBackground(); sourceTask?.cancel()
            } else if phase == .active {
                recording.didBecomeActive()
                if !recording.pendingMemoryDeletion { chat?.didBecomeActive() }
            }
        }
        .onDisappear { dictation.interrupt() }
        .alert("Delete this recording?", isPresented: $confirmingDeletion) {
            Button("Cancel", role: .cancel) {}
            Button("Delete", role: .destructive) {
                sourceTask?.cancel()
                if let selected, recording.deleteFromLibrary(selected) {
                    if chat?.attachment?.session_id == selected.id.uuidString { chat?.attachment = nil }
                    chat?.clearForSourceDeletion()
                    selectedID = nil; citedSource = nil
                    needsChatRefresh = true
                    refreshWhenReady()
                }
            }.accessibilityIdentifier("confirmDeleteSession")
        } message: {
            Text(selected?.source == "personal_text"
                 ? "The personal note and answers that depend on its evidence will be removed."
                 : "The transcript and answers tied to it will be removed. Learned memories and their supporting excerpts may remain with your companion.")
        }
    }

    @ViewBuilder private var chatContent: some View {
        if let chat {
            @Bindable var chat = chat
            VStack(alignment: .leading, spacing: 12) {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 20) {
                        if chat.nextBefore != nil {
                            Button("Earlier messages") { chat.loadEarlier() }.disabled(chat.isBusy)
                        }
                        if chat.turns.isEmpty, chat.response == nil { Text("Talk to your companion.").foregroundStyle(.secondary) }
                        ForEach(chat.turns) { turn in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(turn.question).fontWeight(.semibold)
                                if let answer = turn.answer { Text(CompanionMessageText.presented(answer)).textSelection(.enabled).accessibilityIdentifier("companionAnswer") }
                                if turn.state != .complete { Text(turnLabel(turn.state)).font(.caption).foregroundStyle(.secondary) }
                                ForEach(CompanionMessageText.showsEvidence ? turn.citations : [], id: \.id) { citation in
                                    if citation.source.retained_claim_id != nil {
                                        Text("Memory \(citation.id) · recording deleted")
                                            .font(.caption).foregroundStyle(.secondary)
                                            .accessibilityIdentifier("retainedMemoryReference")
                                    } else {
                                        Button("Source \(citation.id)") { openSource(turn: turn.id, citation: citation.id, owner: chat.owner) }
                                            .accessibilityIdentifier("companionSource")
                                    }
                                }
                            }.id(turn.id)
                        }
                        if let response = chat.response {
                            Text(response.request.question).fontWeight(.semibold)
                            Text(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)).textSelection(.enabled).accessibilityIdentifier("companionPartial")
                            Text(response.state == .saved ? "Saved" : response.state == .uncertain ? "Completion not confirmed" : "Answering…")
                                .font(.caption)
                            if response.memoryStatus == "unavailable" { Text("Past memory is unavailable for this answer.").font(.caption) }
                            if response.state == .uncertain {
                                Button("Recover question") { chat.recoverUncertainResponse() }.disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            }
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }.defaultScrollAnchor(.bottom)
                if let notice = chat.notice ?? sourceNotice { Text(notice).font(.caption).foregroundStyle(.secondary) }
                if let attachment = chat.attachment {
                    HStack {
                        Text("Attached recording").font(.caption).accessibilityIdentifier("chatAttachment")
                        Button("Remove") { chat.attachment = nil }.accessibilityIdentifier("removeAttachment")
                        Button("Open") { selectedID = UUID(uuidString: attachment.session_id); citedSource = nil; surface = "Recordings" }
                    }
                }
                if recording.liveStatus == "Recording" { Text("Includes the transcript received so far.").font(.caption) }
                if dictation.isActive { Text(dictation.state == .starting ? "Preparing dictation…" : dictation.state == .finishing ? "Finishing dictation…" : "Listening for your message…").font(.caption) }
                if let notice = dictation.notice { Text(notice).font(.caption).accessibilityIdentifier("dictationNotice") }
                HStack {
                    Toggle("Use past memory", isOn: $chat.useMemory).font(.caption)
                    Spacer()
                    Button("Clear draft", role: .destructive) {
                        dictation.discard()
                        chat.draft = ""
                    }
                    .disabled(!dictation.isActive && chat.draft.isEmpty)
                    .accessibilityIdentifier("clearCompanionDraft")
                }
                TextField("Talk to companion", text: Binding(
                    get: { ComposerDictation.appending(dictation.text, to: chat.draft) },
                    set: { if !dictation.isActive { chat.draft = $0 } }), axis: .vertical)
                    .disabled(dictation.isActive)
                    .textFieldStyle(.roundedBorder).focused($composing).lineLimit(1...5).accessibilityIdentifier("companionDraft")
                HStack {
                    Button("Send") {
                        if dictation.isActive { dictation.finish(send: true) }
                        else { sendDraft(chat) }
                    }
                        .disabled(chat.isBusy || recording.pendingMemoryDeletion || dictation.state == .starting || dictation.state == .finishing
                                  || ComposerDictation.appending(dictation.text, to: chat.draft).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .accessibilityIdentifier("sendCompanion")
                    if dictation.isActive {
                        Button(dictation.state == .finishing ? "Finishing…" : "Stop dictation") {
                            if dictation.state == .starting { dictation.interrupt() }
                            else { dictation.finish(send: false) }
                        }.disabled(dictation.state == .finishing).accessibilityIdentifier("stopDictation")
                    } else {
                        Button { composing = false; dictation.start { text, send in
                            chat.draft = ComposerDictation.appending(text, to: chat.draft)
                            if send, surface == "Companion", scenePhase == .active,
                               !chat.isBusy, !recording.pendingMemoryDeletion { sendDraft(chat) }
                        } } label: { Label("Dictate", systemImage: "mic") }
                            .disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            .accessibilityIdentifier("startDictation")
                    }
                    if chat.isBusy { Button("Cancel answer") { chat.cancel() } }
                    Spacer()
                    Button("Refresh") { chat.refresh() }.disabled(chat.isBusy || recording.pendingMemoryDeletion)
                }
            }
        } else { Text(sourceNotice ?? "Connecting to your companion…") }
    }

    private func sendDraft(_ chat: CompanionController) {
        composing = false
        chat.send(live: recording.liveStatus == "Recording" ? recording.current : nil)
    }

    private var libraryContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if selectedID != nil {
                    HStack {
                        Button("All recordings") { selectedID = nil; citedSource = nil; sourceNotice = nil }
                            .accessibilityIdentifier("allRecordings")
                        Button("Back to companion") { surface = "Companion" }.accessibilityIdentifier("backToCompanion")
                    }
                    if let session = selected {
                        HStack {
                            Text(session.createdAt.formatted()).font(.headline)
                            Text(recording.isActive && recording.current?.id == session.id ? "Recording" : session.completed ? "Saved" : "Incomplete · saved")
                                .accessibilityIdentifier("librarySessionStatus")
                        }
                        HStack {
                            if let attachment = recording.companionAttachment(for: session), !(recording.isActive && recording.current?.id == session.id) {
                                Button("Ask about this") { chat?.attachment = attachment; surface = "Companion" }
                                    .accessibilityIdentifier("askAboutRecording")
                            } else { Text("Ask about this becomes available after this recording syncs.").font(.caption) }
                            if !(recording.isActive && recording.current?.id == session.id) {
                                Button("Delete recording", role: .destructive) { confirmingDeletion = true }.accessibilityIdentifier("deleteSession")
                            }
                        }
                    }
                    if let citedSource {
                        Text("Cited passage · \(citedSource.start, specifier: "%.1f")s").font(.caption)
                        Text(citedSource.text).padding().background(.quaternary).accessibilityIdentifier("citedPassage")
                        if citedSource.snapshot_id != nil { Text("Transcript excerpt at the time you asked.").font(.caption) }
                    }
                    if let session = selected {
                        let attachment = recording.companionAttachment(for: session)
                        let active = recording.isActive && recording.current?.id == session.id
                        if !active, session.source != "personal_text" {
                            Picker("Recording content", selection: $recordingTab) {
                                Text("Notes").tag("Notes")
                                Text("Transcript").tag("Transcript")
                            }.pickerStyle(.segmented).accessibilityIdentifier("recordingContent")
                        }
                        if recordingTab == "Notes", !active, session.source != "personal_text" {
                            if let attachment {
                                RecordingNotesView(attachment: attachment, configuration: { try Self.config() }, onPassage: { passage in
                                    notePassage = MemorySource(session, revision: attachment.revision).passages.first { $0.id == passage }
                                    recordingTab = "Transcript"
                                }).id("\(attachment.session_id):\(attachment.revision)")
                            } else { Text("Notes become available after this recording syncs.").font(.caption) }
                        } else {
                            if let notePassage {
                                Text("Supporting passage · \(notePassage.start, specifier: "%.1f")s").font(.caption)
                                Text(notePassage.text).padding().background(.quaternary).accessibilityIdentifier("notesSupportingPassage")
                            }
                            ForEach(session.transcript.segments) { segment in
                                VStack(alignment: .leading) {
                                    Text("\(segment.start, specifier: "%.1f")s").font(.caption)
                                    Text(segment.text).textSelection(.enabled)
                                }.accessibilityIdentifier("transcriptSegment")
                            }
                        }
                    } else { Text("The full recording is not available on this device.") }
                } else {
                    Text("Recordings").font(.title2.bold())
                    if library.isEmpty { Text("No recordings yet.") }
                    LazyVStack(alignment: .leading, spacing: 16) {
                        ForEach(library) { session in
                            Button {
                                selectedID = session.id; citedSource = nil
                            } label: {
                                VStack(alignment: .leading) {
                                    RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", configuration: { try Self.config() })
                                    Text(session.createdAt.formatted()).font(.caption)
                                }
                            }.accessibilityIdentifier("savedSession")
                        }
                    }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    private func openSource(turn: String, citation: String, owner: String) {
        sourceTask?.cancel()
        sourceNotice = "Opening source…"
        sourceTask = Task {
            do {
                try await connection(owner: owner).run(.source(turnID: turn, citationID: citation)) { event in
                    try Task.checkCancellation()
                    recordingTab = "Transcript"; notePassage = nil
                    citedSource = event.source
                    selectedID = event.source?.session_id.flatMap(UUID.init(uuidString:))
                    surface = "Recordings"
                    sourceNotice = nil
                }
            } catch { if !Task.isCancelled { sourceNotice = error.localizedDescription } }
        }
    }
    private func refreshWhenReady() {
        guard needsChatRefresh, let chat, !chat.isBusy, !recording.pendingMemoryDeletion else { return }
        needsChatRefresh = false
        chat.refresh()
    }
    private func turnLabel(_ state: CompanionTurn.State) -> String {
        switch state {
        case .complete: "Saved"
        case .pending: "Still processing · refresh to check"
        case .failed: "Answer did not finish"
        case .outdated: "Past answer · its context has changed"
        case .invalidated: "Answer removed because its source changed or was deleted"
        }
    }
}
