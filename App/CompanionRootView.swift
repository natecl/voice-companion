import SwiftUI

/// Notes and Agent share one draft, one conversation, and deliberate capture.
struct CompanionRootView: View {
    @State private var recording = SessionController.forApp()
    @State private var chat: CompanionController?
    @State private var proactive: ProactiveCoordinator?
    @State private var dictation = ComposerDictation.forApp()
    @State private var surface = "Companion"
    @State private var selectedID: UUID?
    @State private var citedSource: CompanionEvidence?
    @State private var sourceNotice: String?
    @State private var searching = false
    @State private var searchText = ""
    @State private var showingAccount = false
    @State private var showingInvite = false
    @State private var showingAttachments = false
    @State private var panelDismissing = false
    @State private var profilePage = "Your space"
    @AppStorage("companionAppearance") private var appearance = "system"
    @State private var toast: String?
    @State private var toastTask: Task<Void, Never>?
    @State private var readyTitles: [UUID: String] = [:]
    @State private var recordingTab = "Notes"
    @State private var notePassage: MemoryPassage?
    @State private var confirmingDeletion = false
    @State private var libraryDeletion: CaptureSession?
    @State private var needsChatRefresh = false
    @State private var sourceTask: Task<Void, Never>?
    @FocusState private var composing: Bool
    @FocusState private var searchingNotes: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accountSignOut) private var signOut

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
    private var pageBackground: Color { ExperienceStyle.canvas }

    var body: some View {
        VStack(spacing: 0) {
            if recording.pendingMemoryDeletion {
                Text("Deleting the source from companion memory… Chat will resume after synchronization.")
                    .font(.caption).padding(.horizontal, 20).accessibilityIdentifier("deletionPending")
            }
            ZStack {
                if surface == "Companion" {
                    VStack(spacing: 0) { navigation; chatContent }.transition(reduceMotion ? .opacity : .move(edge: .trailing).combined(with: .opacity))
                } else {
                    VStack(spacing: 0) { navigation; homeContent }.transition(reduceMotion ? .opacity : .move(edge: .leading).combined(with: .opacity))
                }
            }.clipped().animation(reduceMotion ? nil : .smooth(duration: 0.36), value: surface)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 10) {
                if recording.liveStatus != nil {
                    if panelVisible { captureBar.hidden() } else { captureBar }
                }
                if !searching && surface == "Companion" { composer }
            }.padding(.horizontal, 16).padding(.top, 18).padding(.bottom, 8)
                .background(pageBackground)
        }
        .background(pageBackground)

        .foregroundStyle(ExperienceStyle.ink).tracking(-0.25)
        .tint(ExperienceStyle.ink)
        .buttonStyle(ExperiencePressStyle())
        .frame(minWidth: 300, minHeight: 420)
        .preferredColorScheme(appearance == "system" ? nil : appearance == "dark" ? .dark : .light)
        .scaleEffect(panelVisible && !reduceMotion ? 0.96 : 1, anchor: .top)
        .offset(y: panelVisible && !reduceMotion ? 5 : 0)
        .background(ExperienceStyle.canvas)
        .allowsHitTesting(!panelVisible && !panelDismissing)
        .disabled(panelVisible || panelDismissing)
        .accessibilityElement(children: .contain)
        .accessibilityHidden(panelVisible)
        .overlay { if panelVisible { accessoryPanel.allowsHitTesting(panelVisible) } }
        .overlay(alignment: .bottom) {
            if let toast {
                RoomToast(message: toast) { dismissToast() }
                    .padding(.horizontal, 24).padding(.bottom, 90)
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .animation(reduceMotion ? nil : .timingCurve(0.22, 1, 0.36, 1, duration: panelVisible ? 0.42 : 0.22), value: panelVisible)
        .animation(reduceMotion ? nil : .easeOut(duration: 0.22), value: toast)
        .onChange(of: recording.errorMessage) { _, value in if let value { showToast(value, persistent: true) } }
        .onChange(of: chat?.notice) { _, value in if let value { showToast(value, persistent: true) } }
        .onChange(of: sourceNotice) { _, value in if let value { showToast(value, persistent: true) } }
        .onChange(of: dictation.notice) { _, value in if let value { showToast(value, persistent: true) } }
        .onChange(of: chat?.refreshStatus) { _, value in if let value { showToast(value) } }
        .onChange(of: recording.isActive) { wasActive, active in
            ExperienceHaptics.recordingChanged()
            if wasActive && !active, let current = recording.current {
                selectedID = current.id; recordingTab = "Notes"; citedSource = nil
            }
        }
        .task {
            do {
                let config = try Self.config()
                guard let owner = config.memoryOwnerID else { throw CaptureFailure.noRelay }
                chat = CompanionController(owner: owner, makeConnection: { connection(owner: owner) })
                #if DEBUG
                // Debug-only QA; hosted phone tests additionally require server enrollment and funding.
                if (ProcessInfo.processInfo.arguments.contains("--proactive-qa") && config.url.host == "127.0.0.1") ||
                    ProcessInfo.processInfo.arguments.contains("--proactive-phone-qa") {
                    proactive = ProactiveCoordinator(makeConnection: {
                        ProactiveSocketConnection(configuration: {
                            let current = try Self.config()
                            guard current.memoryOwnerID == owner else { throw AskFailure.accessExpired }
                            return current
                        })
                    }, received: { needsChatRefresh = true; refreshWhenReady() })
                }
                #endif
                if !recording.pendingMemoryDeletion { chat?.refresh() }
                updateProactive()
            } catch { sourceNotice = error.localizedDescription }
        }
        .onChange(of: selected.flatMap { recording.companionAttachment(for: $0) }) { _, _ in notePassage = nil }
        .onChange(of: selectedID) { _, _ in notePassage = nil; recordingTab = citedSource == nil ? "Notes" : "Transcript" }
        .onChange(of: surface) { _, value in if value == "Recordings" { composing = false; dictation.interrupt() } }
        .onChange(of: recording.pendingMemoryDeletion) { _, pending in
            if pending { dictation.interrupt(); proactive?.suspend() }
            else { needsChatRefresh = true; refreshWhenReady() }
        }
        .onChange(of: proactiveSource) { _, _ in updateProactive() }
        .onChange(of: chat?.useMemory) { _, _ in updateProactive() }
        .onChange(of: SharedMicrophone.shared.meetingAudioPaused) { _, _ in updateProactive() }
        .onChange(of: chat?.isBusy) { _, _ in refreshWhenReady() }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { proactive?.suspend() }
            if phase == .background {
                dictation.interrupt(); recording.didEnterBackground(); chat?.didEnterBackground(); sourceTask?.cancel()
            } else if phase == .active {
                recording.didBecomeActive()
                updateProactive()
                if !recording.pendingMemoryDeletion { chat?.didBecomeActive() }
            }
        }
        .onDisappear { dictation.interrupt(); proactive?.suspend() }
        .onReceive(NotificationCenter.default.publisher(for: .accountWillChange)) { _ in
            recording.endAccountSession(); dictation.interrupt(); proactive?.suspend()
            chat?.cancel(); chat?.draft = ""; sourceTask?.cancel(); toastTask?.cancel()
        }

    }

    private var proactiveSource: MemorySource? {
        guard recording.liveStatus == "Recording", let current = recording.current,
              current.memoryOwnerID == chat?.owner else { return nil }
        return MemorySource(live: current, revision: 1, finalizedOnly: true)
    }
    private func updateProactive() {
        guard chat?.useMemory == true else { proactive?.quiet(); return }
        proactive?.update(proactiveSource, foreground: scenePhase == .active &&
            !recording.pendingMemoryDeletion && !SharedMicrophone.shared.meetingAudioPaused)
    }

    private var showingLiveRecording: Bool { recording.isActive && selectedID == recording.current?.id }

    private var panelVisible: Bool { selectedID != nil || showingAttachments || showingInvite || showingAccount }
    private func closePanel() {
        panelDismissing = true
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.22), completionCriteria: .removed) {
            selectedID = nil; citedSource = nil; showingAttachments = false; showingInvite = false; showingAccount = false
        } completion: { panelDismissing = false }
    }
    private var panelTitle: String {
        if selectedID != nil { return showingLiveRecording ? "Live transcript" : "Your note" }
        if showingAttachments { return "Bring a note into the conversation" }
        if showingInvite { return "Invite a friend" }
        return profilePage
    }
    private var panelCloseLabel: String {
        selectedID != nil ? "Close recording" : showingInvite ? "Close invitation" : "Close panel"
    }
    private var accessoryPanel: some View {
        RoomPanel(title: panelTitle, closeLabel: panelCloseLabel, onClose: closePanel) {
            if selectedID != nil { recordingDetail }
            else if showingAttachments { attachmentPicker }
            else if showingInvite { inviteContent }
            else { profileContent }
        }
    }
    private func dismissToast() { toastTask?.cancel(); toast = nil }
    private func showToast(_ message: String, persistent: Bool = false) {
        toastTask?.cancel(); toast = message
        if !persistent {
            toastTask = Task { do { try await Task.sleep(for: .milliseconds(2300)); toast = nil } catch {} }
        }
    }
    private var recordingDetail: some View {
        VStack(alignment: .leading, spacing: 20) {
            libraryContent
            if showingLiveRecording { captureBar }
            if let selected, let attachment = recording.companionAttachment(for: selected), !showingLiveRecording {
                Button { chat?.attachment = attachment; closePanel(); surface = "Companion" } label: {
                    Text("Talk about this").modifier(RoomPrimaryButton())
                }.accessibilityIdentifier("askAboutRecording")
            }
            if citedSource != nil { Button("Back to Agent") { closePanel(); surface = "Companion" }.accessibilityIdentifier("backToCompanion") }
        }
    }

    private static let welcomeMessage = "Hey, good to see you."

    @ViewBuilder private var chatContent: some View {
        if let chat {
            @Bindable var chat = chat
            ScrollViewReader { proxy in
            VStack(alignment: .leading, spacing: 12) {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 8) {
                        if chat.nextBefore != nil {
                            Button("Earlier messages") { chat.loadEarlier() }.disabled(chat.isBusy)
                        }
                        if chat.nextBefore == nil, chat.turns.first.map({ $0.sequence == 1 }) ?? true {
                            Text("Today").font(RoomTypography.body(11)).foregroundStyle(ExperienceStyle.secondary)
                                .frame(maxWidth: .infinity).padding(.bottom, 23)
                            Text(Self.welcomeMessage).modifier(ExperienceAgentBubble())
                                .contextMenu {
                                    Button("Copy", systemImage: "square.on.square") { ExperienceClipboard.copy(Self.welcomeMessage) }
                                }
                                .padding(.trailing, 44).frame(maxWidth: .infinity, alignment: .leading)
                                .accessibilityIdentifier("agentWelcome")
                            Text("What’s on your mind?").modifier(ExperienceAgentBubble(grouped: true))
                                .padding(.trailing, 44).frame(maxWidth: .infinity, alignment: .leading)
                            Text("In a conversation? Tap + to invite me in. You can keep talking here, too.")
                                .font(RoomTypography.body(12)).lineSpacing(3.5).foregroundStyle(ExperienceStyle.secondary)
                                .frame(maxWidth: 245, alignment: .leading).padding(.horizontal, 8).padding(.top, 18)

                        }
                        ForEach(chat.turns) { turn in
                            VStack(alignment: .leading, spacing: 8) {
                                if !turn.isProactive {
                                    Text(turn.question).modifier(RoomUserBubble()).padding(.vertical, 18)
                                }
                                if let answer = turn.answer {
                                    VStack(alignment: .leading, spacing: 6) {
                                        ForEach(Array(CompanionMessageText.bubbles(answer, proactive: turn.isProactive).enumerated()), id: \.offset) { _, message in
                                            Text(message).modifier(ExperienceAgentBubble(grouped: true))
                                                .contextMenu {
                                                    Button("Copy", systemImage: "doc.on.doc") { ExperienceClipboard.copy(message) }
                                                }
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                                .accessibilityIdentifier("companionAnswer")
                                        }
                                    }
                                    .padding(.top, 8).padding(.trailing, 44)
                                }
                                if turn.state == .failed { Button("Answer needs attention") { showToast(turnLabel(turn.state), persistent: true) }.font(RoomTypography.body(12)).foregroundStyle(ExperienceStyle.secondary) }
                                ForEach(CompanionMessageText.showsEvidence ? turn.citations : [], id: \.id) { citation in
                                    if citation.source.retained_claim_id != nil {
                                        Text("Memory \(citation.id) · recording deleted")
                                            .font(.caption).foregroundStyle(ExperienceStyle.secondary)
                                            .accessibilityIdentifier("retainedMemoryReference")
                                    } else {
                                        Button("Source \(citation.id)") { openSource(turn: turn.id, citation: citation.id, owner: chat.owner) }
                                            .accessibilityIdentifier("companionSource")
                                    }
                                }
                            }.id(turn.id)
                        }
                        if let response = chat.response {
                            Text(response.request.question).modifier(RoomUserBubble()).padding(.vertical, 18)
                            if !response.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            Text(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)).modifier(ExperienceAgentBubble())
                                .contextMenu {
                                    Button("Copy", systemImage: "doc.on.doc") { ExperienceClipboard.copy(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)) }
                                }
                                .padding(.trailing, 44).frame(maxWidth: .infinity, alignment: .leading)
                                .accessibilityIdentifier("companionPartial")
                            }
                            if response.state == .streaming { ExperienceThinkingStatus(label: "Answering…", active: surface == "Companion" && selectedID == nil) }
                            else if response.state != .saved {
                                Color.clear.frame(height: 0).onAppear {
                                    showToast("Reply interrupted. Check whether it was saved.", persistent: true)
                                }
                            }

                            if response.state == .uncertain {
                                Button("Check reply") { chat.recoverUncertainResponse(); dismissToast() }
                                    .font(RoomTypography.body(13)).padding(.horizontal, 16).padding(.vertical, 10)
                                    .background(ExperienceStyle.card, in: Capsule())
                                    .disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            }
                        }
                    }.padding(.horizontal, 20).padding(.top, 9).padding(.bottom, 25).frame(maxWidth: 760, alignment: .leading).frame(maxWidth: .infinity)
                }.scrollDismissesKeyboard(.interactively).defaultScrollAnchor(.bottom).defaultScrollAnchor(.top, for: .alignment)
                if let id = proactive?.latestMessageID, chat.turns.contains(where: { $0.id == id }) {
                    Button { proxy.scrollTo(id, anchor: .bottom); proactive?.markRead() } label: {
                        Label("New message", systemImage: "arrow.down")
                            .font(.callout).padding(.horizontal, 14).padding(.vertical, 8)
                            .background(ExperienceStyle.card, in: Capsule())
                            .overlay(Capsule().strokeBorder(ExperienceStyle.line, lineWidth: 1))
                    }.frame(maxWidth: .infinity).padding(.bottom, 8)
                        .accessibilityIdentifier("proactiveNewMessage")
                }
            }
            }
        } else {
            Text("Connecting…").font(RoomTypography.body(13)).foregroundStyle(ExperienceStyle.secondary).frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    @ViewBuilder private var composer: some View {
        if let chat {
            @Bindable var chat = chat
            VStack(alignment: .leading, spacing: 8) {
                if proactive?.unavailable == true {
                    Text("Proactive reminders are unavailable for this capture. You can still ask me.")
                        .font(.caption).foregroundStyle(ExperienceStyle.secondary)
                }
                if let attachment = chat.attachment {
                    HStack(spacing: 8) {
                        Button { selectedID = UUID(uuidString: attachment.session_id); citedSource = nil } label: {
                            RecordingLibraryTitle(attachment: attachment, personal: false, configuration: { try Self.config() })
                                .font(RoomTypography.body(12)).lineLimit(1).accessibilityIdentifier("chatAttachment")
                        }
                        Spacer(minLength: 0)
                        Button { chat.attachment = nil } label: { RoomIcon(name: "close").frame(width: 36, height: 34) }
                            .accessibilityLabel("Remove attachment").accessibilityIdentifier("removeAttachment")
                    }.padding(.leading, 14).padding(.trailing, 10).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 18))
                }
                if dictation.isActive {
                    Text(dictation.state == .starting ? "Preparing dictation…" : dictation.state == .finishing ? "Finishing dictation…" : "Listening for your message…")
                        .font(.caption).accessibilityIdentifier("dictationStatus")
                }
                if recording.liveStatus == "Recording", SharedMicrophone.shared.meetingAudioPaused {
                    Text("Meeting capture is paused while you dictate. It resumes automatically.")
                        .font(.caption).accessibilityIdentifier("meetingDictationPause")
                }
                HStack(alignment: .bottom, spacing: 10) {
                    HStack(alignment: .bottom, spacing: 0) {
                        if dictation.isActive {
                            ExperienceIconButton("Discard dictation", icon: "trash", bare: true) { dictation.discard() }
                                .accessibilityIdentifier("discardDictation")
                            Text(String(format: "%d:%02d", dictation.elapsedSeconds / 60, dictation.elapsedSeconds % 60))
                                .font(.callout.weight(.medium)).monospacedDigit().foregroundStyle(ExperienceStyle.secondary)
                                .frame(height: 44).accessibilityLabel("Dictation duration")
                            HStack(spacing: 3) {
                                ForEach(dictation.levels.indices, id: \.self) { index in
                                    Capsule().fill(ExperienceStyle.ink)
                                        .frame(maxWidth: 4).frame(height: 3 + dictation.levels[index] * 23)
                                }
                            }.frame(maxWidth: .infinity).frame(height: 44).padding(.horizontal, 8)
                                .accessibilityLabel("Microphone level").accessibilityIdentifier("dictationWaveform")
                            RoomComposerButton("Send", icon: "arrow.up", filled: true) { dictation.finish(send: true) }
                                .disabled(dictation.state != .listening || recording.pendingMemoryDeletion)
                                .accessibilityIdentifier("sendDictation")
                        } else {
                        Button { composing = false; showingAttachments = true } label: {
                            RoomIcon(name: "paperclip").rotationEffect(.degrees(-45)).frame(width: 38, height: 44).contentShape(Rectangle())
                        }.accessibilityLabel("Attach note").accessibilityIdentifier("chooseRecordingAttachment")
                        TextField("Message Ellis", text: Binding(
                            get: { ComposerDictation.appending(dictation.text, to: chat.draft) },
                            set: { if !dictation.isActive { chat.draft = $0 } }), prompt: Text("Message Ellis").foregroundStyle(ExperienceStyle.secondary), axis: .vertical)
                            .textFieldStyle(.plain).font(RoomTypography.body(16)).tracking(0).padding(.vertical, 11).disabled(dictation.isActive)
                            .focused($composing).lineLimit(1...5).frame(maxWidth: .infinity).accessibilityIdentifier("companionDraft")
                        ZStack {
                            Group {
                                if chat.isBusy {
                                    ExperienceIconButton(chat.isRefreshing ? "Cancel refresh" : "Cancel answer", icon: "stop.fill") { chat.cancel() }
                                } else if !chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                                    RoomComposerButton("Send", icon: "arrow.up", filled: true) { sendDraft(chat) }
                                        .disabled(recording.pendingMemoryDeletion)
                                        .accessibilityIdentifier("sendCompanion")
                                } else {
                                    RoomComposerButton("Dictate message", icon: "mic") {
                                        startDictation(chat)
                                    }.disabled(recording.pendingMemoryDeletion).accessibilityIdentifier("startDictation")
                                }
                            }.id(dictation.isActive ? "dictation" : chat.isBusy ? "busy" : chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "mic" : "send")
                                .transition(reduceMotion ? .opacity : .scale(scale: 0.86).combined(with: .opacity))
                        }.frame(width: 38, height: 44)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: dictation.isActive)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: chat.isBusy)
                        }
                    }.padding(5)
                        .background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 29, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 29, style: .continuous).strokeBorder(ExperienceStyle.line, lineWidth: 1))
                        .shadow(color: ExperienceStyle.ink.opacity(0.045), radius: 16, y: 6)
                    if recording.liveStatus == nil {
                        ExperienceIconButton("Capture meeting note", icon: "plus", filled: true, size: 58) {
                            composing = false; dictation.interrupt(); surface = "Companion"; recording.startRecording()
                        }.accessibilityIdentifier("startRecording")
                    }
                }
            }
        } else {
            HStack {
                Text("Your companion connection is not configured.").font(.caption)
                Spacer()
                ExperienceIconButton("Capture meeting note", icon: "plus", filled: true, size: 58) { recording.startRecording() }
                    .accessibilityIdentifier("startRecording")
            }
        }
    }

    private func startDictation(_ chat: CompanionController) {
        composing = false
        dictation.start { text, send in
            chat.draft = ComposerDictation.appending(text, to: chat.draft)
            if send, scenePhase == .active, !chat.isBusy, !recording.pendingMemoryDeletion { sendDraft(chat) }
        }
    }

    private func sendDraft(_ chat: CompanionController) {
        composing = false
        surface = "Companion"
        chat.send(live: recording.liveStatus == "Recording" ? recording.current : nil)
    }

    private var libraryContent: some View {
            VStack(alignment: .leading, spacing: 16) {
                if selectedID != nil {

                    if let session = selected {
                        if !(recording.isActive && recording.current?.id == session.id) {
                            Group {
                                if let title = readyTitles[session.id] { Text(title) }
                                else { RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", configuration: { try Self.config() }) }
                            }.font(.custom("Georgia", size: 29)).tracking(-1)
                                .fixedSize(horizontal: false, vertical: true)
                                .frame(maxWidth: .infinity, alignment: .leading).padding(.top, 4).accessibilityIdentifier("notesTitle")
                        } else { Text("Transcribing live").font(.callout).foregroundStyle(ExperienceStyle.secondary) }
                        if !(recording.isActive && recording.current?.id == session.id) { HStack {
                            Text(dayTitle(session.createdAt) + (session.recordingSeconds.map { " · \(Int($0 / 60)) minutes" } ?? "")).font(RoomTypography.body(13)).foregroundStyle(ExperienceStyle.secondary)
                            if !session.completed && !recording.isActive { Text("Incomplete · saved").font(.caption).accessibilityIdentifier("librarySessionStatus") }
                        } }

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
                            HStack(spacing: 0) {
                                ForEach(["Notes", "Transcript"], id: \.self) { tab in
                                    Button { recordingTab = tab } label: {
                                        Text(tab).font(RoomTypography.body(13)).foregroundStyle(recordingTab == tab ? ExperienceStyle.ink : ExperienceStyle.secondary)
                                            .frame(maxWidth: .infinity).frame(height: 36)
                                            .background(recordingTab == tab ? ExperienceStyle.card : Color.clear, in: Capsule())
                                            .shadow(color: .black.opacity(recordingTab == tab ? 0.035 : 0), radius: 6, y: 2)
                                    }.accessibilityAddTraits(recordingTab == tab ? .isSelected : [])
                                }
                            }.padding(4).background(ExperienceStyle.surface, in: Capsule()).accessibilityIdentifier("recordingContent")
                        }
                        if recordingTab == "Notes", !active, session.source != "personal_text" {
                            if let attachment {
                                RecordingNotesView(attachment: attachment, configuration: { try Self.config() }, onPassage: { passage in
                                    notePassage = MemorySource(session, revision: attachment.revision).passages.first { $0.id == passage }
                                    recordingTab = "Transcript"
                                }, onTitle: { readyTitles[session.id] = $0 }).id("\(attachment.session_id):\(attachment.revision)")
                            } else { Text("Notes become available after this recording syncs.").font(.caption) }
                        } else {
                            if let notePassage {
                                Text("Supporting passage · \(notePassage.start, specifier: "%.1f")s").font(.caption)
                                Text(notePassage.text).padding().background(.quaternary).accessibilityIdentifier("notesSupportingPassage")
                            }
                            if session.transcript.segments.isEmpty {
                                Text(active ? "Listening. Transcript will appear here as speech is received." : "No transcript was received.")
                                    .foregroundStyle(ExperienceStyle.secondary).padding(.vertical, 16)
                            }
                            if let notice = session.stopNotice { Text(notice).font(.caption).foregroundStyle(ExperienceStyle.secondary) }
                            VStack(alignment: .leading, spacing: 18) {
                            ForEach(session.transcript.segments) { segment in
                                VStack(alignment: .leading, spacing: 6) {
                                    ForEach(Array(segment.speakerTurns.enumerated()), id: \.offset) { _, turn in
                                        VStack(alignment: .leading, spacing: 6) {
                                            if session.source != "personal_text" {
                                                Text(String(format: "%02d:%02d", Int(segment.start) / 60, Int(segment.start) % 60) + " · " + (turn.speaker.map { "Speaker \($0 + 1)" } ?? "Speaker unknown"))
                                                    .font(.caption.weight(.medium))
                                                    .foregroundStyle(ExperienceStyle.secondary)
                                                    .accessibilityIdentifier("transcriptSpeaker")
                                            }
                                            Text(turn.text).font(RoomTypography.body(15)).lineSpacing(5.3).textSelection(.enabled)
                                        }.padding(.bottom, 6)
                                    }
                                }.accessibilityIdentifier("transcriptSegment")
                            }
                            }.padding(23).frame(maxWidth: .infinity, alignment: .leading).background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 24))
                        }
                    } else { Text("The full recording is not available on this device.") }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
    }
    @ViewBuilder private var navigation: some View {
        if surface == "Recordings" {
            ZStack {
                Text("Notes").font(.system(size: 17, weight: .medium))
                HStack {
                    ExperienceIconButton("Back to Ellis", icon: "arrow.left", size: 46) {
                        searching = false; searchText = ""
                        withAnimation(reduceMotion ? nil : .smooth(duration: 0.44)) { surface = "Companion" }
                    }.accessibilityIdentifier("agentNavigation")
                    Spacer()
                    ExperienceIconButton("Search notes", icon: "magnifyingglass", size: 46) { searching = true; searchingNotes = true }
                        .accessibilityIdentifier("searchRecordings")
                }
            }.padding(.horizontal, 18).padding(.top, 14).padding(.bottom, 12)
        } else {
            ZStack(alignment: .top) {
                HStack(alignment: .top) {
                    ExperienceIconButton("Open notes", icon: "equal", size: 46) {
                        withAnimation(reduceMotion ? nil : .smooth(duration: 0.44)) { surface = "Recordings" }
                    }.accessibilityIdentifier("notesNavigation")
                    Spacer()
                    Button { composing = false; showingInvite = true } label: {
                        Text("Invite").font(.system(size: 14, weight: .medium))
                            .padding(.horizontal, 18).frame(height: 46)
                            .background(ExperienceStyle.card, in: Capsule())
                            .overlay(Capsule().strokeBorder(ExperienceStyle.line.opacity(0.65), lineWidth: 1))
                    }.accessibilityIdentifier("inviteFriends")
                }.padding(.horizontal, 16).padding(.top, 14)
                Button { composing = false; profilePage = "Your space"; showingAccount = true } label: {
                    VStack(spacing: 2) {
                        companionPortrait
                        Text("Ellis").font(.system(size: 14, weight: .medium))
                    }.frame(width: 110)
                }.padding(.top, 3).accessibilityLabel("Account").accessibilityIdentifier("companionProfile")
                    .contextMenu { Button("Refresh conversation") { chat?.refresh(userInitiated: true) }.disabled(chat?.isBusy ?? true) }
            }.frame(height: 126, alignment: .top)
        }
    }

    @ViewBuilder private var companionPortrait: some View {
        #if DEBUG
        // Founder-approved reference artwork for the internal design study only.
        Image("CompanionStudy").resizable().scaledToFit().frame(width: 76, height: 72)
            .offset(y: recording.liveStatus == "Recording" ? -2 : 0)
            .shadow(color: ExperienceStyle.accent.opacity(recording.liveStatus == "Recording" ? 0.25 : 0.10), radius: recording.liveStatus == "Recording" ? 9 : 5, y: 6)
            .animation(reduceMotion ? nil : .smooth(duration: 0.55), value: recording.liveStatus == "Recording")
            .accessibilityHidden(true)
        #else
        Text("E").font(.system(size: 34, weight: .medium, design: .serif))
            .frame(width: 70, height: 70).background(ExperienceStyle.surface, in: Circle())
            .accessibilityHidden(true)
        #endif
    }

    private var inviteContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("A little more company.").modifier(RoomTitle())
            Text("Friend invitations aren’t available in this internal build yet.").font(RoomTypography.body(15)).lineSpacing(5.3)
            Button { showingInvite = false; profilePage = "Your space"; showingAccount = true } label: {
                HStack { Text("Your profile"); Spacer(); RoomIcon(name: "chevron-right") }.modifier(RoomRow())
            }.accessibilityIdentifier("yourProfile")
        }
    }
    private var profileContent: some View {
        VStack(alignment: .leading, spacing: 18) {
            if profilePage == "What Ellis remembers" {
                Text("You’re in control.").modifier(RoomTitle())
                Text("Ellis uses your captured conversations to remember relevant context. You can choose whether past memory informs your conversations.").lineSpacing(5.3)
                if let chat { @Bindable var chat = chat
                    Toggle("Use past memory", isOn: $chat.useMemory).modifier(RoomRow())
                }
                Text("Deleting a note removes its transcript. Existing replies and learned memories may remain.").lineSpacing(5.3).foregroundStyle(ExperienceStyle.secondary)
            } else {
                Text("Good to have you here.").modifier(RoomTitle())
                VStack(spacing: 0) {
                    Button { appearance = appearance == "dark" ? "light" : "dark"; closePanel() } label: {
                        HStack { Text("Appearance"); Spacer(); Text(appearance.capitalized).foregroundStyle(ExperienceStyle.secondary) }.modifier(RoomRow())
                    }.accessibilityIdentifier("roomAppearance")
                    Button { profilePage = "What Ellis remembers" } label: {
                        HStack { Text("What Ellis remembers"); Spacer(); RoomIcon(name: "chevron-right") }.modifier(RoomRow())
                    }
                    if let signOut {
                        Button(action: signOut) { HStack { Text("Sign out"); Spacer() }.modifier(RoomRow()) }
                    }
                }.padding(23).background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 24))

            }
        }.font(RoomTypography.body(15))
    }
    private var attachmentPicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            if library.isEmpty {
                Text("No notes yet").font(.system(size: 17, weight: .medium))
                Text("Capture a conversation to create your first note.").font(RoomTypography.body(14)).foregroundStyle(ExperienceStyle.secondary)
            }
            ForEach(library) { session in
                let attachment = recording.companionAttachment(for: session)
                Button { chat?.attachment = attachment; closePanel(); surface = "Companion" } label: {
                    VStack(alignment: .leading, spacing: 8) {
                        RecordingLibraryTitle(attachment: attachment, personal: session.source == "personal_text", configuration: { try Self.config() }).font(.system(size: 17, weight: .medium))
                        Text(attachment == nil ? "Available after synchronization" : recordingMetadata(session)).font(RoomTypography.body(14)).foregroundStyle(ExperienceStyle.secondary)
                    }.frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 20).padding(.vertical, 21)
                        .background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 27))
                }.disabled(attachment == nil).accessibilityIdentifier("attachRecordingRow")
            }
        }
    }

    private var homeContent: some View {
        List {
            Group {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(spacing: 12) {
                        RoomIcon(name: "magnifyingglass").foregroundStyle(ExperienceStyle.secondary)
                        TextField("Find a conversation", text: $searchText, prompt: Text("Find a conversation").foregroundStyle(ExperienceStyle.secondary)).textFieldStyle(.plain)
                            .font(RoomTypography.body(16)).focused($searchingNotes).submitLabel(.search)
                            .onSubmit { searchingNotes = false }.accessibilityIdentifier("recordingSearch")
                        if searching || !searchText.isEmpty {
                            Button("Cancel") { searchText = ""; searching = false; searchingNotes = false }
                                .font(RoomTypography.body(12)).foregroundStyle(ExperienceStyle.secondary)
                        }
                    }.frame(height: 46).padding(.horizontal, 2)
                        .overlay(alignment: .bottom) { Rectangle().fill(ExperienceStyle.line).frame(height: 1) }
                        .padding(.bottom, 26)
                    Text("Your notes").font(.custom("Georgia", size: 30)).tracking(-1).padding(.bottom, 9)
                    Text("The conversations you can come back to.").font(RoomTypography.body(13))
                        .foregroundStyle(ExperienceStyle.secondary).padding(.bottom, 10)
                }

                let matches = library.filter { searchText.isEmpty || $0.transcript.segments.contains { $0.text.localizedCaseInsensitiveContains(searchText) } }
                if matches.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(searchText.isEmpty ? "Your conversations will find a home here." : "No matching recordings")
                        Text(searchText.isEmpty ? "Tap + with Ellis to capture your first conversation." : "Try another word from the transcript.")
                    }.font(RoomTypography.body(15)).foregroundStyle(ExperienceStyle.secondary).padding(.vertical, 30)
                }
                if searching { Text("\(matches.count) \(matches.count == 1 ? "result" : "results")").font(.footnote.weight(.semibold)).foregroundStyle(ExperienceStyle.secondary).padding(.vertical, 18) }
                ForEach(Array(matches.enumerated()), id: \.element.id) { index, session in
                    if !searching && (index == 0 || dayTitle(session.createdAt) != dayTitle(matches[index - 1].createdAt)) {
                        Text(dayTitle(session.createdAt)).font(RoomTypography.body(13)).foregroundStyle(ExperienceStyle.secondary).padding(.top, 26).padding(.bottom, 13)
                    }
                    Button { composing = false; selectedID = session.id; citedSource = nil } label: {
                        VStack(alignment: .leading, spacing: 9) {
                            RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", refreshKey: "\(surface):\(selectedID?.uuidString ?? "")", configuration: { try Self.config() })
                                .font(.system(size: 17, weight: .medium)).foregroundStyle(ExperienceStyle.ink)
                            Text(searchPreview(session))
                                .font(RoomTypography.body(14)).lineSpacing(4).foregroundStyle(ExperienceStyle.secondary).lineLimit(3)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Text(recordingMetadata(session)).font(.caption).foregroundStyle(ExperienceStyle.secondary)
                                .padding(.top, 7)
                        }.padding(.vertical, 21).padding(.horizontal, 20).frame(maxWidth: .infinity, alignment: .leading)
                            .background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 27, style: .continuous))
                            .overlay { RoundedRectangle(cornerRadius: 27, style: .continuous).stroke(ExperienceStyle.line.opacity(0.55), lineWidth: 0.5) }
                            .contentShape(RoundedRectangle(cornerRadius: 27, style: .continuous))
                    }.buttonStyle(ExperiencePressStyle(pressedScale: 0.985)).accessibilityIdentifier("savedSession")
                    #if os(iOS)
                    .contentShape(.contextMenuPreview, RoundedRectangle(cornerRadius: 27, style: .continuous))
                    #endif
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button { ExperienceClipboard.copy(noteExport(session)) } label: { noteActionLabel("Copy", icon: "square.on.square").labelStyle(.iconOnly) }
                            .buttonStyle(.automatic).tint(ExperienceStyle.secondary)
                        ShareLink(item: noteExport(session)) { noteActionLabel("Share", icon: "arrowshape.turn.up.right").labelStyle(.iconOnly) }
                            .buttonStyle(.automatic).tint(.blue)
                        if !(recording.isActive && recording.current?.id == session.id) {
                            Button { libraryDeletion = session } label: { noteActionLabel("Delete", icon: "trash").labelStyle(.iconOnly) }
                                .buttonStyle(.automatic).tint(.red)
                        }
                    }
                    .contextMenu {
                        if !(recording.isActive && recording.current?.id == session.id) {
                            Button(role: .destructive) { libraryDeletion = session } label: { noteActionLabel("Delete", icon: "trash") }
                        }
                        ShareLink(item: noteExport(session)) { noteActionLabel("Share", icon: "arrowshape.turn.up.right") }
                        Button { ExperienceClipboard.copy(noteExport(session)) } label: { noteActionLabel("Copy", icon: "square.on.square") }
                    }
                    .padding(.bottom, 10)
                }
            }
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 0, trailing: 20))
            .listRowSeparator(.hidden).listRowBackground(Color.clear)
        }.listStyle(.plain).scrollContentBackground(.hidden)
            .environment(\.defaultMinListRowHeight, 0)
            .frame(maxWidth: 760).frame(maxWidth: .infinity)
            .scrollDismissesKeyboard(.interactively)
            .alert("Delete this note?", isPresented: Binding(get: { libraryDeletion != nil }, set: { if !$0 { libraryDeletion = nil } }), presenting: libraryDeletion) { note in
                Button("Cancel", role: .cancel) { libraryDeletion = nil }
                Button("Delete", role: .destructive) { deleteNote(note); libraryDeletion = nil }
                    .accessibilityIdentifier("confirmDeleteLibraryNote")
            } message: { _ in
                Text("The note and transcript will be removed. Your conversation and learned memories will stay.")
            }
    }

    private func noteActionLabel(_ title: String, icon: String) -> some View {
        Label { Text(title) } icon: {
            Image(systemName: icon).environment(\.symbolVariants, .none)
                .font(.system(size: 20, weight: .medium))
        }
    }

    private func noteExport(_ session: CaptureSession) -> String {
        session.transcript.segments.map(\.text).joined(separator: "\n")
    }

    private func deleteNote(_ note: CaptureSession) {
        sourceTask?.cancel()
        let deleted = withAnimation(reduceMotion ? nil : .smooth(duration: 0.24)) {
            recording.deleteFromLibrary(note)
        }
        guard deleted else { return }
        if chat?.attachment?.session_id == note.id.uuidString { chat?.attachment = nil }
        if selectedID == note.id { selectedID = nil; citedSource = nil }
        needsChatRefresh = true
        refreshWhenReady()
    }

    private func searchPreview(_ session: CaptureSession) -> AttributedString {
        let text = (searching && !searchText.isEmpty ? session.transcript.segments.first { $0.text.localizedCaseInsensitiveContains(searchText) }?.text : nil) ?? session.transcript.segments.first?.text ?? "Waiting for transcript…"
        var result = AttributedString(text)
        if searching, !searchText.isEmpty, let range = result.range(of: searchText, options: [.caseInsensitive, .diacriticInsensitive]) { result[range].backgroundColor = ExperienceStyle.surface }
        return result
    }

    private func recordingMetadata(_ session: CaptureSession) -> String {
        let time = session.createdAt.formatted(date: .omitted, time: .shortened)
        guard let seconds = session.recordingSeconds else { return time }
        return time + " · " + (seconds < 60 ? "\(Int(seconds)) sec" : "\(Int(seconds / 60)) min")
    }

    private func dayTitle(_ date: Date) -> String {
        if Calendar.current.isDateInToday(date) { return "Today" }
        if Calendar.current.isDateInYesterday(date) { return "Yesterday" }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    private var captureBar: some View {
        HStack(spacing: 5) {
            Button { composing = false; selectedID = recording.current?.id; citedSource = nil; recordingTab = "Transcript" } label: {
                HStack(spacing: 7) {
                    Circle().fill(Color.red).frame(width: 12, height: 12)
                        .padding(5).background(Color.red.opacity(0.10), in: Circle())
                    Text(SharedMicrophone.shared.meetingAudioPaused ? "Paused for dictation" : (recording.liveStatus == "Recording" ? "Listening" : recording.liveStatus ?? "Saved")).font(RoomTypography.body(12))
                    TimelineView(.periodic(from: .now, by: 1)) { _ in
                        let seconds = Int(recording.elapsedRecordingSeconds)
                        Text(String(format: "%d:%02d", seconds / 60, seconds % 60)).monospacedDigit().font(RoomTypography.body(11)).foregroundStyle(ExperienceStyle.secondary)
                    }
                    Spacer(minLength: 0)
                    Text("View").font(RoomTypography.body(12)).padding(.horizontal, 10)
                }.frame(minHeight: 44).contentShape(Rectangle())
            }.accessibilityLabel("Open live transcript").accessibilityIdentifier("showActiveRecording")
            ExperienceIconButton(proactive == nil ? "Contributions unavailable" : proactive?.isQuiet == true ? "Contributions quiet" : "Quiet contributions", icon: proactive?.isQuiet == true ? "bell.slash" : "bell", bare: true, size: 38) { proactive?.quiet() }
                .disabled(proactive == nil || proactive?.isQuiet == true)
                .accessibilityIdentifier("quietContributions")
            ExperienceIconButton("Stop recording", icon: "stop.fill", size: 38) { recording.stop() }
                .disabled(recording.liveStatus != "Recording").accessibilityIdentifier("stopRecording")
        }.padding(.leading, 12).padding(.trailing, 7).padding(.vertical, 6).frame(minHeight: 58)
            .background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 25))
            .overlay(RoundedRectangle(cornerRadius: 25).strokeBorder(ExperienceStyle.line, lineWidth: 1))
            .shadow(color: ExperienceStyle.ink.opacity(0.02), radius: 20, y: 4)
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
        case .invalidated: "Past answer"
        }
    }
}
