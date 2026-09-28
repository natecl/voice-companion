import SwiftUI

/// Notes and Agent share one draft, one conversation, and deliberate capture.
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
    @State private var showingAttachments = false
    @State private var readyTitles: [UUID: String] = [:]
    @State private var recordingTab = "Notes"
    @State private var recordingDetent: PresentationDetent = .large
    @State private var notePassage: MemoryPassage?
    @State private var confirmingDeletion = false
    @State private var libraryDeletion: CaptureSession?
    @State private var needsChatRefresh = false
    @State private var sourceTask: Task<Void, Never>?
    @FocusState private var composing: Bool
    @Namespace private var navigationSelection
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
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
    private var pageBackground: Color { surface == "Recordings" ? Color(white: 0.97) : ExperienceStyle.canvas }

    var body: some View {
        VStack(spacing: 0) {
            navigation.padding(.horizontal, 16).padding(.vertical, 2)
            if let error = recording.errorMessage {
                ExperienceNotice(title: "Recording needs attention", message: error).padding(.horizontal, 20)
            }
            if recording.pendingMemoryDeletion {
                Text("Deleting the source from companion memory… Chat will resume after synchronization.")
                    .font(.caption).padding(.horizontal, 20).accessibilityIdentifier("deletionPending")
            }
            ZStack {
                chatContent.opacity(surface == "Companion" ? 1 : 0)
                    .offset(x: reduceMotion || surface == "Companion" ? 0 : -10)
                    .allowsHitTesting(surface == "Companion").accessibilityHidden(surface != "Companion")
                homeContent.opacity(surface == "Recordings" ? 1 : 0)
                    .offset(x: reduceMotion || surface == "Recordings" ? 0 : 10)
                    .allowsHitTesting(surface == "Recordings").accessibilityHidden(surface != "Recordings")
            }.animation(reduceMotion ? nil : .easeInOut(duration: 0.18), value: surface)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 12) {
                if recording.liveStatus != nil, selectedID == nil { captureBar }
                if !searching { composer }
            }.padding(.horizontal, 18).padding(.top, 14).padding(.bottom, 14)
                .background(pageBackground)
        }
        .background(pageBackground)
        .preferredColorScheme(.light)
        .foregroundStyle(ExperienceStyle.ink)
        .tint(ExperienceStyle.ink)
        .buttonStyle(ExperiencePressStyle())
        .frame(minWidth: 300, minHeight: 420)
        .accessibilityHidden(selectedID != nil || showingAccount || showingAttachments)
        .sheet(isPresented: Binding(get: { selectedID != nil && showingLiveRecording }, set: { if !$0 && showingLiveRecording { selectedID = nil; citedSource = nil } })) { recordingDetail }
        .overlay {
            if selectedID != nil && !showingLiveRecording { recordingDetail.transition(.opacity) }
        }
        .sheet(isPresented: $showingAttachments) { attachmentPicker }
        .overlay { if showingAccount { accountContent.background(ExperienceStyle.canvas).transition(.opacity) } }
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.2), value: showingAccount)
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.2), value: selectedID)
        .onChange(of: recording.isActive) { wasActive, active in
            ExperienceHaptics.recordingChanged()
            if wasActive && !active, let current = recording.current {
                recordingDetent = .large; selectedID = current.id; recordingTab = "Notes"; citedSource = nil
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
            if pending { dictation.interrupt() }
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

    private var showingLiveRecording: Bool { recording.isActive && selectedID == recording.current?.id }

    private var recordingDetail: some View {
            VStack(spacing: 16) {
                HStack(spacing: 12) {
                    if showingLiveRecording {
                        Text("Live transcript").font(.system(size: 25, weight: .bold)); Spacer()
                        ExperienceIconButton("Close recording", icon: "xmark") { selectedID = nil; citedSource = nil }
                    } else {
                        ExperienceIconButton("Close recording", icon: "chevron.left") { selectedID = nil; citedSource = nil }
                        if let selected {
                            RecordingLibraryTitle(attachment: recording.companionAttachment(for: selected), personal: selected.source == "personal_text", configuration: { try Self.config() })
                                .font(.callout.weight(.semibold)).lineLimit(1).padding(.horizontal, 14).frame(height: 44)
                                .background(.white, in: Capsule()).shadow(color: .black.opacity(0.055), radius: 16, y: 7)
                            Spacer(minLength: 0)
                            ShareLink(item: selected.transcript.segments.map(\.text).joined(separator: "\n")) { Image(systemName: "arrowshape.turn.up.right").font(.system(size: 20)).frame(width: 40, height: 44) }
                            Menu {
                                Button("Delete recording", role: .destructive) { confirmingDeletion = true }.accessibilityIdentifier("deleteSession")
                            } label: { Image(systemName: "ellipsis").font(.system(size: 20, weight: .semibold)).frame(width: 40, height: 44) }.accessibilityLabel("Recording options")
                        }
                    }
                }.padding(.horizontal, 16).padding(.top, showingLiveRecording ? 24 : 2)
                libraryContent.padding(.horizontal, 18)
                if recording.liveStatus != nil { captureBar.padding(16) }
                HStack {
                    if citedSource != nil {
                        Button("Back to Agent") { selectedID = nil; surface = "Companion" }.accessibilityIdentifier("backToCompanion")
                    }
                    if let selected, let attachment = recording.companionAttachment(for: selected), !(recording.isActive && selected.id == recording.current?.id) {
                        Button { chat?.attachment = attachment; selectedID = nil; surface = "Companion" } label: {
                            HStack {
                                Text("Ask Agent about this note").font(.callout).foregroundStyle(ExperienceStyle.secondary)
                                Spacer()
                                Image(systemName: "arrow.up").font(.system(size: 20, weight: .semibold)).foregroundStyle(.white).frame(width: 40, height: 40).background(ExperienceStyle.ink, in: Circle())
                            }.padding(10).padding(.leading, 7).experienceCard(radius: 28, elevated: true)
                        }.accessibilityIdentifier("askAboutRecording")
                    }
                }.padding(.horizontal, 24).padding(.bottom, 16)

            }
            .buttonStyle(ExperiencePressStyle()).background(ExperienceStyle.canvas).tint(ExperienceStyle.ink)
            .presentationDetents([.fraction(0.68), .large], selection: $recordingDetent).presentationDragIndicator(.visible)
            .frame(minWidth: 300, minHeight: 420)
            .alert("Delete this recording?", isPresented: $confirmingDeletion) {
                Button("Cancel", role: .cancel) {}
                Button("Delete", role: .destructive) {
                    if let selected { deleteNote(selected) }
                }.accessibilityIdentifier("confirmDeleteSession")
            } message: {
                Text(selected?.source == "personal_text"
                     ? "The note will be removed. Your conversation will stay."
                     : "The note and transcript will be removed. Your conversation and learned memories will stay.")
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
                        if chat.turns.isEmpty, chat.response == nil { VStack(alignment: .leading, spacing: 12) { Text("What’s on your mind?").font(.title2.weight(.semibold)); Text("Talk things through, or capture a conversation to come back to.").foregroundStyle(ExperienceStyle.secondary) }.padding(.vertical, 48) }
                        ForEach(chat.turns) { turn in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(turn.question).padding(.horizontal, 14).padding(.vertical, 12).experienceCard(radius: 18).frame(maxWidth: .infinity, alignment: .trailing)
                                if let answer = turn.answer {
                                    Text(CompanionMessageText.presented(answer)).modifier(ExperienceAgentBubble())
                                        .contextMenu {
                                            Button("Copy", systemImage: "doc.on.doc") { ExperienceClipboard.copy(CompanionMessageText.presented(answer)) }
                                        }
                                        .padding(.top, 14).padding(.trailing, 32)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .accessibilityIdentifier("companionAnswer")
                                }
                                if turn.state == .pending || turn.state == .failed { ExperienceNotice(title: "About this answer", message: turnLabel(turn.state)) }
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
                            Text(response.request.question).padding(.horizontal, 14).padding(.vertical, 12).experienceCard(radius: 18).frame(maxWidth: .infinity, alignment: .trailing)
                            Text(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)).modifier(ExperienceAgentBubble())
                                .contextMenu {
                                    Button("Copy", systemImage: "doc.on.doc") { ExperienceClipboard.copy(CompanionMessageText.presented(response.text, streaming: response.state == .streaming)) }
                                }
                                .padding(.trailing, 32).frame(maxWidth: .infinity, alignment: .leading)
                                .accessibilityIdentifier("companionPartial")
                            if response.state == .streaming { ExperienceThinkingStatus(label: "Answering…", active: surface == "Companion" && selectedID == nil) }
                            else if response.state != .saved { ExperienceNotice(title: "Answer interrupted", message: "We couldn’t confirm this answer was saved. Recover the question below to check or continue it.") }

                            if response.state == .uncertain {
                                Button("Recover question") { chat.recoverUncertainResponse() }.disabled(chat.isBusy || recording.pendingMemoryDeletion)
                            }
                        }
                    }.padding(24).frame(maxWidth: 760, alignment: .leading).frame(maxWidth: .infinity)
                }.scrollDismissesKeyboard(.interactively).defaultScrollAnchor(.bottom).defaultScrollAnchor(chat.turns.isEmpty && chat.response == nil ? .center : .top, for: .alignment)
            }
        } else {
            ContentUnavailableView("Your companion", systemImage: "bubble.left", description: Text(sourceNotice ?? "Connecting…"))
        }
    }

    @ViewBuilder private var composer: some View {
        if let chat {
            @Bindable var chat = chat
            VStack(alignment: .leading, spacing: 8) {
                if let status = chat.refreshStatus {
                    HStack(spacing: 8) {
                        if chat.isRefreshing { ProgressView().controlSize(.small) }
                        else { Image(systemName: "checkmark.circle") }
                        Text(status).font(.caption)
                    }.foregroundStyle(ExperienceStyle.secondary).accessibilityIdentifier("conversationRefreshStatus")
                }
                if let notice = chat.notice ?? sourceNotice { ExperienceNotice(title: "Agent update", message: notice).accessibilityIdentifier("companionNotice") }
                if let attachment = chat.attachment {
                    HStack(spacing: 12) {
                        Label("Attached note", systemImage: "doc.text").font(.caption).accessibilityIdentifier("chatAttachment")
                        Button("Open") { selectedID = UUID(uuidString: attachment.session_id); citedSource = nil }
                        Spacer()
                        Button("Remove") { chat.attachment = nil }.accessibilityIdentifier("removeAttachment")
                    }.font(.caption).padding(10).background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 14))
                }
                if dictation.isActive {
                    Text(dictation.state == .starting ? "Preparing dictation…" : dictation.state == .finishing ? "Finishing dictation…" : "Listening for your message…")
                        .font(.caption).accessibilityIdentifier("dictationStatus")
                }
                if let notice = dictation.notice { ExperienceNotice(title: "Dictation update", message: notice).accessibilityIdentifier("dictationNotice") }
                if recording.liveStatus == "Recording", SharedMicrophone.shared.meetingAudioPaused {
                    Text("Meeting capture is paused while you dictate. It resumes automatically.")
                        .font(.caption).accessibilityIdentifier("meetingDictationPause")
                }
                HStack(alignment: .bottom, spacing: 8) {
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
                            ExperienceIconButton("Send", icon: "arrow.up", filled: true) { dictation.finish(send: true) }
                                .disabled(dictation.state != .listening || recording.pendingMemoryDeletion)
                                .accessibilityIdentifier("sendDictation")
                        } else {
                        Menu {
                            Button("Attach note", systemImage: "doc.text") { composing = false; showingAttachments = true }
                                .accessibilityIdentifier("chooseRecordingAttachment")
                            Divider()
                            Toggle("Use past memory", isOn: $chat.useMemory)
                            Button("Refresh chat", systemImage: "arrow.clockwise") { composing = false; chat.refresh(userInitiated: true) }.accessibilityLabel("Refresh conversation").disabled(chat.isBusy || recording.pendingMemoryDeletion)
                        } label: { Image(systemName: "paperclip").font(.system(size: 20, weight: .regular)).rotationEffect(.degrees(-45)).frame(width: 44, height: 44).contentShape(Rectangle()) }
                            .accessibilityLabel("Attachments and message options")
                        TextField("Message Agent", text: Binding(
                            get: { ComposerDictation.appending(dictation.text, to: chat.draft) },
                            set: { if !dictation.isActive { chat.draft = $0 } }), prompt: Text("Message Agent").foregroundStyle(ExperienceStyle.secondary), axis: .vertical)
                            .textFieldStyle(.plain).font(.callout).padding(.vertical, 11).disabled(dictation.isActive)
                            .focused($composing).lineLimit(1...5).frame(maxWidth: .infinity).accessibilityIdentifier("companionDraft")
                        ZStack {
                            Group {
                                if chat.isBusy {
                                    ExperienceIconButton(chat.isRefreshing ? "Cancel refresh" : "Cancel answer", icon: "stop.fill") { chat.cancel() }
                                } else if !chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                                    ExperienceIconButton("Send", icon: "arrow.up", filled: true) { sendDraft(chat) }
                                        .disabled(recording.pendingMemoryDeletion)
                                        .accessibilityIdentifier("sendCompanion")
                                } else {
                                    ExperienceIconButton("Dictate message", icon: "mic", bare: true) {
                                        startDictation(chat)
                                    }.disabled(recording.pendingMemoryDeletion).accessibilityIdentifier("startDictation")
                                }
                            }.id(dictation.isActive ? "dictation" : chat.isBusy ? "busy" : chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "mic" : "send")
                                .transition(reduceMotion ? .opacity : .scale(scale: 0.86).combined(with: .opacity))
                        }.frame(width: 44, height: 44)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: chat.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: dictation.isActive)
                            .animation(reduceMotion ? nil : .smooth(duration: 0.2), value: chat.isBusy)
                        }
                    }.padding(.horizontal, 4).padding(.vertical, 3)
                        .background(.white, in: RoundedRectangle(cornerRadius: 24))
                        .overlay(RoundedRectangle(cornerRadius: 24).strokeBorder(ExperienceStyle.line, lineWidth: 1))
                        .shadow(color: .black.opacity(0.075), radius: 20, y: 8)
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
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if selectedID != nil {

                    if let session = selected {
                        if !(recording.isActive && recording.current?.id == session.id) {
                            Group {
                                if let title = readyTitles[session.id] { Text(title) }
                                else { RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", configuration: { try Self.config() }) }
                            }.font(.system(size: 30, weight: .semibold, design: .serif)).padding(.top, 20).accessibilityIdentifier("notesTitle")
                        } else { Text("Transcribing live").font(.callout).foregroundStyle(ExperienceStyle.secondary) }
                        if !(recording.isActive && recording.current?.id == session.id) { HStack {
                            Text(dayTitle(session.createdAt) + (session.recordingSeconds.map { " · \(Int($0 / 60)) minutes" } ?? "")).font(.subheadline).foregroundStyle(ExperienceStyle.secondary)
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
                                        Text(tab).font(.callout.weight(.medium)).foregroundStyle(recordingTab == tab ? ExperienceStyle.ink : ExperienceStyle.secondary)
                                            .frame(maxWidth: .infinity).frame(height: 38)
                                            .background(recordingTab == tab ? Color.white : Color.clear, in: Capsule())
                                            .shadow(color: .black.opacity(recordingTab == tab ? 0.035 : 0), radius: 6, y: 2)
                                    }.accessibilityAddTraits(recordingTab == tab ? .isSelected : [])
                                }
                            }.padding(2).background(ExperienceStyle.surface, in: Capsule()).accessibilityIdentifier("recordingContent")
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
                            ForEach(session.transcript.segments) { segment in
                                VStack(alignment: .leading) {
                                    Text(String(format: "%02d:%02d", Int(segment.start) / 60, Int(segment.start) % 60)).font(.caption).foregroundStyle(ExperienceStyle.secondary).padding(.bottom, 5)
                                    Text(segment.text).font(.body).lineSpacing(3).textSelection(.enabled)
                                }.padding(.vertical, 10).accessibilityIdentifier("transcriptSegment")
                            }
                        }
                    } else { Text("The full recording is not available on this device.") }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    @ViewBuilder private var navigation: some View {
        if searching {
            HStack(spacing: 16) {
                ExperienceIconButton("Cancel", icon: "chevron.left") { searchText = ""; searching = false }
                HStack(spacing: 12) {
                    ExperienceSymbol(name: "magnifyingglass").frame(width: 22, height: 22)
                    TextField("Search transcripts", text: $searchText).textFieldStyle(.plain).focused($composing).submitLabel(.search).onSubmit { composing = false }.accessibilityIdentifier("recordingSearch")
                    Button { searchText = "" } label: { Image(systemName: "xmark").foregroundStyle(ExperienceStyle.secondary).frame(width: 30, height: 30).background(ExperienceStyle.surface, in: Circle()) }.accessibilityLabel("Clear search")
                }.padding(.horizontal, 14).frame(height: 44).experienceCard(radius: 22)
            }
        } else if surface == "Recordings" {
            HStack(spacing: 12) {
                ExperienceIconButton("Back to Agent", icon: "chevron.left") {
                    withAnimation(reduceMotion ? nil : .smooth(duration: 0.24)) { surface = "Companion" }
                }.accessibilityIdentifier("agentNavigation")
                Text("Notes").font(.headline).padding(.horizontal, 18).frame(height: 44)
                    .background(.white, in: Capsule()).shadow(color: .black.opacity(0.05), radius: 16, y: 7)
                Spacer(minLength: 0)
                HStack(spacing: 4) {
                    ExperienceIconButton("Search recordings", icon: "magnifyingglass", bare: true) { searching = true }.accessibilityIdentifier("searchRecordings")
                    Menu {
                        Button("Account") { showingAccount = true }
                    } label: { Image(systemName: "ellipsis").font(.system(size: 21, weight: .semibold)).frame(width: 44, height: 44) }.accessibilityLabel("Notes options")
                }.padding(.horizontal, 5).background(.white, in: Capsule()).shadow(color: .black.opacity(0.05), radius: 16, y: 7)
            }
        } else {
        HStack(spacing: 6) {
            ExperienceIconButton("Account", icon: "person") { composing = false; showingAccount = true }
            Spacer(minLength: 8)
            navigationPill("Agent", icon: "bubble.left", value: "Companion", identifier: "agentNavigation")
                .contextMenu {
                    if let answer = chat?.turns.last?.answer { ShareLink(item: CompanionMessageText.presented(answer)) }
                    Button("Refresh chat") { chat?.refresh(userInitiated: true) }.accessibilityLabel("Refresh conversation").disabled(chat?.isBusy ?? true)
                }
            navigationPill("Notes", icon: "doc.text", value: "Recordings", identifier: "notesNavigation")
            Spacer(minLength: 8)
            ExperienceIconButton("Search recordings", icon: "magnifyingglass") { surface = "Recordings"; searching.toggle() }
                .accessibilityIdentifier("searchRecordings")
        }
        }
    }

    private func navigationPill(_ title: String, icon: String, value: String, identifier: String) -> some View {
        Button { withAnimation(reduceMotion ? nil : .snappy(duration: 0.24, extraBounce: 0)) { surface = value } } label: {
            HStack(spacing: 9) {
                ExperienceSymbol(name: icon).frame(width: 22, height: 22)
                Text(title).font(.system(size: 15, weight: surface == value ? .semibold : .medium))
            }.padding(.horizontal, 17).frame(height: 42)
                .background {
                    if surface == value {
                        Capsule().fill(ExperienceStyle.surface).matchedGeometryEffect(id: "selectedRootTab", in: navigationSelection)
                    }
                }
                .overlay(Capsule().strokeBorder(surface == value ? .clear : ExperienceStyle.line, lineWidth: 1))
        }.buttonStyle(ExperiencePressStyle()).accessibilityIdentifier(identifier).accessibilityAddTraits(surface == value ? .isSelected : [])
    }

    private var attachmentPicker: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    if library.isEmpty { ContentUnavailableView("No notes yet", systemImage: "doc.text", description: Text("Capture a conversation to create your first note.")) }
                    if !library.isEmpty {
                        Text("Choose a note to give Agent context for your message.")
                            .font(.subheadline).foregroundStyle(ExperienceStyle.secondary).padding(.bottom, 12)
                    }
                    ForEach(library) { session in
                        let attachment = recording.companionAttachment(for: session)
                        Button {
                            chat?.attachment = attachment; showingAttachments = false
                        } label: {
                            HStack(spacing: 16) {
                                ExperienceSymbol(name: "doc.text").frame(width: 24, height: 28)
                                VStack(alignment: .leading, spacing: 5) {
                                    RecordingLibraryTitle(attachment: attachment, personal: session.source == "personal_text", configuration: { try Self.config() }).font(.headline)
                                    Text(attachment == nil ? "Available after synchronization" : session.createdAt.formatted()).font(.caption).foregroundStyle(ExperienceStyle.secondary)
                                }
                                Spacer()
                                Image(systemName: chat?.attachment?.session_id == session.id.uuidString ? "checkmark.circle.fill" : "plus.circle")
                                    .foregroundStyle(ExperienceStyle.secondary)
                            }.padding(.vertical, 18).contentShape(Rectangle())
                        }.disabled(attachment == nil).accessibilityIdentifier("attachRecordingRow")
                        Divider()
                    }
                }.padding(20)
            }.experienceNavigationTitle("Attach note")
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { showingAttachments = false } } }
                .background(ExperienceStyle.canvas)
        }.tint(ExperienceStyle.ink).presentationDetents([.medium, .large])
    }

    private var homeContent: some View {
        List {
            Group {
                let matches = library.filter { searchText.isEmpty || $0.transcript.segments.contains { $0.text.localizedCaseInsensitiveContains(searchText) } }
                if matches.isEmpty {
                    ContentUnavailableView(searchText.isEmpty ? "Keep what matters" : "No matching recordings", systemImage: "doc.text", description: Text(searchText.isEmpty ? "Tap + to capture a conversation. Your saved notes will appear here." : "Try another word from the transcript."))
                }
                if searching { Text("\(matches.count) \(matches.count == 1 ? "result" : "results")").font(.footnote.weight(.semibold)).foregroundStyle(ExperienceStyle.secondary).padding(.vertical, 18) }
                ForEach(Array(matches.enumerated()), id: \.element.id) { index, session in
                    if !searching && (index == 0 || dayTitle(session.createdAt) != dayTitle(matches[index - 1].createdAt)) {
                        Text(dayTitle(session.createdAt)).font(.footnote.weight(.semibold)).foregroundStyle(ExperienceStyle.secondary).padding(.top, index == 0 ? 8 : 14).padding(.bottom, 10)
                    }
                    Button { ExperienceHaptics.tap(); composing = false; recordingDetent = .large; selectedID = session.id; citedSource = nil } label: {
                        VStack(alignment: .leading, spacing: 9) {
                            RecordingLibraryTitle(attachment: recording.companionAttachment(for: session), personal: session.source == "personal_text", refreshKey: "\(surface):\(selectedID?.uuidString ?? "")", configuration: { try Self.config() })
                                .font(.callout.weight(.semibold)).foregroundStyle(ExperienceStyle.ink)
                            Text(searchPreview(session))
                                .font(.callout).foregroundStyle(ExperienceStyle.secondary).lineLimit(3)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Text(recordingMetadata(session)).font(.caption).foregroundStyle(ExperienceStyle.secondary)
                                .padding(.top, 5)
                        }.padding(18).frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white, in: RoundedRectangle(cornerRadius: 24))
                            .overlay { RoundedRectangle(cornerRadius: 24).stroke(ExperienceStyle.line.opacity(0.55), lineWidth: 0.5) }
                            .contentShape(RoundedRectangle(cornerRadius: 24))
                    }.buttonStyle(.plain).accessibilityIdentifier("savedSession")
                    .padding(.bottom, 12)
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
                }
            }
            .listRowInsets(EdgeInsets(top: 0, leading: 20, bottom: 0, trailing: 20))
            .listRowSeparator(.hidden).listRowBackground(Color.clear)
        }.listStyle(.plain).scrollContentBackground(.hidden)
            .environment(\.defaultMinListRowHeight, 0)
            .padding(.top, 10).frame(maxWidth: 760).frame(maxWidth: .infinity)
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
        guard recording.deleteFromLibrary(note) else { return }
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
        HStack(spacing: 12) {
            Button { composing = false; recordingDetent = .fraction(0.68); selectedID = recording.current?.id; citedSource = nil; recordingTab = "Transcript" } label: {
                HStack(spacing: 10) {
                    Circle().fill(.red).frame(width: 14, height: 14)
                    Text(SharedMicrophone.shared.meetingAudioPaused ? "Paused for dictation" : recording.liveStatus ?? "Saved").font(.subheadline.weight(.medium))
                    TimelineView(.periodic(from: .now, by: 1)) { _ in
                        let seconds = Int(recording.elapsedRecordingSeconds)
                        Text(String(format: "%d:%02d", seconds / 60, seconds % 60)).monospacedDigit().font(.subheadline)
                    }
                    Spacer(minLength: 0)
                    Text("View").font(.callout)
                }.frame(minHeight: 44).contentShape(Rectangle())
            }.accessibilityLabel("Open live transcript").accessibilityIdentifier("showActiveRecording")
            ExperienceIconButton("Stop recording", icon: "stop.fill") { recording.stop() }
                .disabled(recording.liveStatus != "Recording").accessibilityIdentifier("stopRecording")
        }.padding(.horizontal, 18).padding(.vertical, 6)
            .background(.white, in: Capsule()).shadow(color: .black.opacity(0.07), radius: 20, y: 8)
    }

    private var accountContent: some View {
        ExperienceAccountView(useMemory: Binding(get: { chat?.useMemory ?? false }, set: { chat?.useMemory = $0 }), recordingLimit: recording.recordingLimit.components.seconds) { showingAccount = false }
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
