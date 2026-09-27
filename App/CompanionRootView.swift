import SwiftUI

/// Home and Agent share one draft, one conversation, and deliberate capture.
struct CompanionRootView: View {
    @State private var recording = SessionController.forApp()
    @State private var chat: CompanionController?
    @State private var dictation = ComposerDictation.forApp()
    @State private var surface = "Companion"
    @State private var selectedID: UUID?
    @State private var citedSource: CompanionEvidence?
    @State private var sourceNotice: String?
    @State private var searching = false
    @State private var searchText = ""
    @State private var showingAccount = false
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
        VStack(spacing: 0) {
            navigation.padding(.horizontal, 20).padding(.vertical, 12)
            if let error = recording.errorMessage {
                Text(error).font(.callout).foregroundStyle(.red).padding(.horizontal, 20)
            }
            if recording.pendingMemoryDeletion {
                Text("Deleting the source from companion memory… Chat will resume after synchronization.")
                    .font(.caption).padding(.horizontal, 20).accessibilityIdentifier("deletionPending")
            }
            ZStack {
                chatContent.opacity(surface == "Companion" ? 1 : 0)
                    .allowsHitTesting(surface == "Companion").accessibilityHidden(surface != "Companion")
                homeContent.opacity(surface == "Recordings" ? 1 : 0)
                    .allowsHitTesting(surface == "Recordings").accessibilityHidden(surface != "Recordings")
            }
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 12) {
                if recording.liveStatus != nil, selectedID == nil { captureBar }
                composer
            }.padding(.horizontal, 16).padding(.top, 12).padding(.bottom, 10)
                .background(.regularMaterial)
        }
        .background(ExperienceStyle.canvas)
        .preferredColorScheme(.light)
        .foregroundStyle(ExperienceStyle.ink)
        .tint(ExperienceStyle.ink)
        .buttonStyle(.plain)
        .frame(minWidth: 300, minHeight: 420)
        .accessibilityHidden(selectedID != nil || showingAccount)
        .sheet(isPresented: Binding(get: { selectedID != nil }, set: { if !$0 { selectedID = nil; citedSource = nil } })) {
            VStack(spacing: 16) {
                HStack {
                    Text(recording.isActive && selectedID == recording.current?.id ? "Live transcript" : "Recording")
                        .font(.title2.weight(.semibold))
                    Spacer()
                    if let selected, !(recording.isActive && selected.id == recording.current?.id) {
                        Menu {
                            Button("Delete recording", role: .destructive) { confirmingDeletion = true }.accessibilityIdentifier("deleteSession")
                        } label: { Image(systemName: "ellipsis").frame(width: 44, height: 44) }.accessibilityLabel("Recording options")
                    }
                    ExperienceIconButton("Close recording", icon: "xmark") { selectedID = nil; citedSource = nil }
                }.padding(.horizontal, 24).padding(.top, 24)
                libraryContent.padding(.horizontal, 24)
                if recording.liveStatus != nil { captureBar.padding(16) }
                HStack {
                    Button("Back to Agent") { selectedID = nil; surface = "Companion" }
                        .accessibilityIdentifier("backToCompanion")
                    Spacer()
                    if let selected, let attachment = recording.companionAttachment(for: selected), !(recording.isActive && selected.id == recording.current?.id) {
                        Button { chat?.attachment = attachment; selectedID = nil; surface = "Companion" } label: {
                            Label("Ask Agent", systemImage: "bubble.left").font(.subheadline.weight(.semibold)).padding(14)
                                .foregroundStyle(.white).background(ExperienceStyle.ink, in: Capsule())
                        }.accessibilityIdentifier("askAboutRecording")
                    }
                }.padding(.horizontal, 24).padding(.bottom, 16)

            }
            .background(ExperienceStyle.canvas).tint(ExperienceStyle.ink)
            .presentationDetents([.large]).presentationDragIndicator(.visible)
            .frame(minWidth: 300, minHeight: 420)
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
        .sheet(isPresented: $showingAccount) {
            accountContent
        }
        .onChange(of: recording.isActive) { wasActive, active in
            if wasActive && !active, let current = recording.current {
                selectedID = current.id; recordingTab = "Notes"; citedSource = nil
            }
        }
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
                        if chat.turns.isEmpty, chat.response == nil { VStack(alignment: .leading, spacing: 12) { Text("What’s on your mind?").font(.largeTitle.weight(.semibold)); Text("Talk things through, or capture a conversation to come back to.").foregroundStyle(.secondary) }.padding(.vertical, 48) }
                        ForEach(chat.turns) { turn in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(turn.question).padding(16).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 22)).frame(maxWidth: .infinity, alignment: .trailing)
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
                            Text(response.request.question).padding(16).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 22)).frame(maxWidth: .infinity, alignment: .trailing)
                            Text(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)).textSelection(.enabled).accessibilityIdentifier("companionPartial")
                            if response.state == .streaming { ExperienceThinkingStatus(label: "Answering…", active: surface == "Companion" && selectedID == nil) }
                            else { Text(response.state == .saved ? "Saved" : "Completion not confirmed").font(.caption) }
                            if response.memoryStatus == "unavailable" { Text("Past memory is unavailable for this answer.").font(.caption) }
                            if response.state == .uncertain {
                                Button("Recover question") { chat.recoverUncertainResponse() }.disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            }
                        }
                    }.padding(24).frame(maxWidth: 760, alignment: .leading).frame(maxWidth: .infinity)
                }.scrollDismissesKeyboard(.interactively).defaultScrollAnchor(.bottom)
            }
        } else {
            ContentUnavailableView("Your companion", systemImage: "bubble.left", description: Text(sourceNotice ?? "Connecting…"))
        }
    }

    @ViewBuilder private var composer: some View {
        if let chat {
            @Bindable var chat = chat
            VStack(alignment: .leading, spacing: 8) {
                if let notice = chat.notice ?? sourceNotice { Text(notice).font(.caption).foregroundStyle(.secondary) }
                if let attachment = chat.attachment {
                    HStack(spacing: 12) {
                        Label("Attached recording", systemImage: "doc.text").font(.caption).accessibilityIdentifier("chatAttachment")
                        Button("Open") { selectedID = UUID(uuidString: attachment.session_id); citedSource = nil }
                        Spacer()
                        Button("Remove") { chat.attachment = nil }.accessibilityIdentifier("removeAttachment")
                    }.font(.caption).padding(10).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 14))
                }
                if dictation.isActive {
                    Text(dictation.state == .starting ? "Preparing dictation…" : dictation.state == .finishing ? "Finishing dictation…" : "Listening for your message…")
                        .font(.caption).accessibilityIdentifier("dictationStatus")
                }
                if let notice = dictation.notice { Text(notice).font(.caption).accessibilityIdentifier("dictationNotice") }
                if recording.liveStatus == "Recording", SharedMicrophone.shared.meetingAudioPaused {
                    Text("Meeting capture is paused while you dictate. It resumes automatically.")
                        .font(.caption).accessibilityIdentifier("meetingDictationPause")
                }
                HStack(alignment: .bottom, spacing: 12) {
                    VStack(alignment: .leading, spacing: 10) {
                        TextField("Message Agent", text: Binding(
                            get: { ComposerDictation.appending(dictation.text, to: chat.draft) },
                            set: { if !dictation.isActive { chat.draft = $0 } }), axis: .vertical)
                            .textFieldStyle(.plain).font(.body).disabled(dictation.isActive)
                            .focused($composing).lineLimit(1...4).accessibilityIdentifier("companionDraft")
                        HStack(spacing: 8) {
                            Menu {
                                Toggle("Use past memory", isOn: $chat.useMemory)
                                Button("Clear draft", role: .destructive) { dictation.discard(); chat.draft = "" }
                                    .disabled(!dictation.isActive && chat.draft.isEmpty).accessibilityIdentifier("clearCompanionDraft")
                                Button("Refresh conversation") { chat.refresh() }.disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            } label: { Image(systemName: "slider.horizontal.3").frame(width: 44, height: 44) }
                                .accessibilityLabel("Message options")
                            Spacer(minLength: 0)
                            if dictation.isActive {
                                ExperienceIconButton("Stop dictation", icon: "stop.fill") {
                                    if dictation.state == .starting { dictation.interrupt() } else { dictation.finish(send: false) }
                                }.disabled(dictation.state == .finishing).accessibilityIdentifier("stopDictation")
                            } else {
                                ExperienceIconButton("Dictate message", icon: "mic") {
                                    composing = false
                                    dictation.start { text, send in
                                        chat.draft = ComposerDictation.appending(text, to: chat.draft)
                                        if send, scenePhase == .active, !chat.isBusy, !recording.pendingMemoryDeletion { sendDraft(chat) }
                                    }
                                }.disabled(chat.isBusy || recording.pendingMemoryDeletion).accessibilityIdentifier("startDictation")
                            }
                            if chat.isBusy {
                                ExperienceIconButton("Cancel answer", icon: "stop.fill") { chat.cancel() }
                            } else {
                                ExperienceIconButton("Send", icon: "arrow.up", filled: true) {
                                    if dictation.isActive { dictation.finish(send: true) } else { sendDraft(chat) }
                                }
                                .disabled(recording.pendingMemoryDeletion || dictation.state == .starting || dictation.state == .finishing || ComposerDictation.appending(dictation.text, to: chat.draft).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                                .accessibilityIdentifier("sendCompanion")
                            }
                        }
                    }.padding(14).background(.white, in: RoundedRectangle(cornerRadius: 28))
                        .overlay(RoundedRectangle(cornerRadius: 28).strokeBorder(ExperienceStyle.line, lineWidth: 1))
                    if recording.liveStatus == nil {
                        ExperienceIconButton("Capture meeting note", icon: "plus", filled: true, size: 56) {
                            composing = false; dictation.interrupt(); surface = "Companion"; recording.startRecording()
                        }.accessibilityIdentifier("startRecording")
                    }
                }
            }
        } else {
            HStack {
                Text("Set up your companion connection in Account.").font(.caption)
                Spacer()
                ExperienceIconButton("Capture meeting note", icon: "plus", filled: true, size: 56) { recording.startRecording() }
                    .accessibilityIdentifier("startRecording")
            }
        }
    }

    private func sendDraft(_ chat: CompanionController) {
        composing = false
        surface = "Companion"
        chat.send(live: recording.liveStatus == "Recording" ? recording.current : nil)
    }

    private var libraryContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if selectedID != nil {

                    if let session = selected {
                        HStack {
                            Text(session.createdAt.formatted(date: .abbreviated, time: .shortened)).font(.subheadline).foregroundStyle(.secondary)
                            Text(recording.isActive && recording.current?.id == session.id ? "Recording" : session.completed ? "Saved" : "Incomplete · saved")
                                .accessibilityIdentifier("librarySessionStatus")
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
                            if session.transcript.segments.isEmpty {
                                Text(active ? "Listening. Transcript will appear here as speech is received." : "No transcript was received.")
                                    .foregroundStyle(.secondary).padding(.vertical, 16)
                            }
                            if let notice = session.stopNotice { Text(notice).font(.caption).foregroundStyle(.secondary) }
                            ForEach(session.transcript.segments) { segment in
                                VStack(alignment: .leading) {
                                    Text("\(segment.start, specifier: "%.1f")s").font(.caption)
                                    Text(segment.text).textSelection(.enabled)
                                }.accessibilityIdentifier("transcriptSegment")
                            }
                        }
                    } else { Text("The full recording is not available on this device.") }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    private var navigation: some View {
        HStack(spacing: 8) {
            ExperienceIconButton("Account", icon: "person.crop.circle") { composing = false; showingAccount = true }
            Spacer(minLength: 0)
            Button { surface = "Recordings" } label: {
                Label("Home", systemImage: "house").font(.subheadline.weight(.semibold)).padding(.horizontal, 14).frame(minHeight: 44)
                    .background(surface == "Recordings" ? ExperienceStyle.surface : .clear, in: Capsule())
            }.accessibilityIdentifier("homeNavigation").accessibilityAddTraits(surface == "Recordings" ? .isSelected : [])
            Button { surface = "Companion" } label: {
                Label("Agent", systemImage: "bubble.left").font(.subheadline.weight(.semibold)).padding(.horizontal, 14).frame(minHeight: 44)
                    .background(surface == "Companion" ? ExperienceStyle.surface : .clear, in: Capsule())
            }.accessibilityIdentifier("agentNavigation").accessibilityAddTraits(surface == "Companion" ? .isSelected : [])
            Spacer(minLength: 0)
            ExperienceIconButton("Search recordings", icon: "magnifyingglass") { surface = "Recordings"; searching.toggle() }
                .accessibilityIdentifier("searchRecordings")
        }
    }

    private var homeContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                if searching {
                    HStack {
                        Image(systemName: "magnifyingglass")
                        TextField("Search transcripts", text: $searchText).textFieldStyle(.plain).accessibilityIdentifier("recordingSearch")
                        Button("Cancel") { searchText = ""; searching = false }
                    }.padding(14).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 16))
                }
                let matches = library.filter { searchText.isEmpty || $0.transcript.segments.contains { $0.text.localizedCaseInsensitiveContains(searchText) } }
                if matches.isEmpty {
                    ContentUnavailableView(searchText.isEmpty ? "Keep what matters" : "No matching recordings", systemImage: "doc.text", description: Text(searchText.isEmpty ? "Tap + to capture a conversation. Your saved notes will appear here." : "Try another word from the transcript."))
                }
                ForEach(Array(matches.enumerated()), id: \.element.id) { index, session in
                    if index == 0 || dayTitle(session.createdAt) != dayTitle(matches[index - 1].createdAt) {
                        Text(dayTitle(session.createdAt)).font(.subheadline.weight(.semibold)).foregroundStyle(.secondary).padding(.top, 8)
                    }
                    Button { composing = false; selectedID = session.id; citedSource = nil } label: {
                        HStack(alignment: .top, spacing: 18) {
                            Image(systemName: "doc.text").font(.system(size: 26, weight: .regular)).frame(width: 32).padding(.top, 3)
                            VStack(alignment: .leading, spacing: 7) {
                                RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", refreshKey: "\(surface):\(selectedID?.uuidString ?? "")", configuration: { try Self.config() })
                                    .font(.headline)
                                Text(session.createdAt.formatted(date: .omitted, time: .shortened)).font(.subheadline).foregroundStyle(.secondary)
                                Text(session.transcript.segments.first?.text ?? "Waiting for transcript…")
                                    .font(.subheadline).foregroundStyle(.secondary).lineLimit(2)
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }.contentShape(Rectangle()).padding(.bottom, 20)
                            .overlay(alignment: .bottom) { Rectangle().fill(ExperienceStyle.line).frame(height: 1) }
                    }.accessibilityIdentifier("savedSession")
                }
            }.padding(24).frame(maxWidth: 760).frame(maxWidth: .infinity)
        }.scrollDismissesKeyboard(.interactively)
    }

    private func dayTitle(_ date: Date) -> String {
        if Calendar.current.isDateInToday(date) { return "Today" }
        if Calendar.current.isDateInYesterday(date) { return "Yesterday" }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    private var captureBar: some View {
        HStack(spacing: 12) {
            Button { composing = false; selectedID = recording.current?.id; citedSource = nil; recordingTab = "Transcript" } label: {
                HStack(spacing: 10) {
                    Circle().fill(.red).frame(width: 10, height: 10)
                    Text(SharedMicrophone.shared.meetingAudioPaused ? "Paused for dictation" : recording.liveStatus ?? "Saved").font(.subheadline.weight(.medium))
                    TimelineView(.periodic(from: .now, by: 1)) { _ in
                        let seconds = Int(recording.elapsedRecordingSeconds)
                        Text(String(format: "%d:%02d", seconds / 60, seconds % 60)).monospacedDigit().font(.subheadline)
                    }
                    Spacer(minLength: 0)
                    Image(systemName: "chevron.up").font(.caption)
                }.frame(minHeight: 44).contentShape(Rectangle())
            }.accessibilityLabel("Open live transcript").accessibilityIdentifier("showActiveRecording")
            ExperienceIconButton("Stop recording", icon: "stop.fill") { recording.stop() }
                .disabled(recording.liveStatus != "Recording").accessibilityIdentifier("stopRecording")
        }.padding(.horizontal, 14).padding(.vertical, 5)
            .background(.white, in: Capsule()).overlay(Capsule().strokeBorder(ExperienceStyle.line, lineWidth: 1))
    }

    private var accountContent: some View {
        NavigationStack {
            Form {
                Section("Companion") {
                    if let chat {
                        @Bindable var chat = chat
                        Toggle("Use past memory", isOn: $chat.useMemory)
                        Text("Your questions stay in your conversation. Dictated questions are kept out of meeting notes.").font(.callout).foregroundStyle(.secondary)
                    } else { Text(sourceNotice ?? "Companion connection is not configured.") }
                }
                Section("Recording") {
                    Text("Capture starts only when you tap +.")
                    Text("This development build stops recordings after \(recording.recordingLimit.components.seconds) seconds.")
                        .foregroundStyle(.secondary)
                }
                Section("Account and subscription") {
                    Text("This build uses an enrolled companion connection. Sign-in and subscriptions are not connected yet.").foregroundStyle(.secondary)
                    NavigationLink("Sign-up preview") { ExperienceSignupView() }
                    NavigationLink("Plan preview") { ExperiencePricingView() }
                }
            }.navigationTitle("Account")
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { showingAccount = false } } }
        }.frame(minWidth: 320, minHeight: 480)
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
