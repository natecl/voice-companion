#if os(iOS)
import SwiftUI
import Observation

/// Native capabilities for the shared presentation; no provider or capture implementation is duplicated.
@MainActor @Observable
final class RoomWebModel {
    let recording = SessionController.forApp()
    let dictation = ComposerDictation.forApp()
    var chat: CompanionController?
    var proactive: ProactiveCoordinator?
    var appearance = ProcessInfo.processInfo.arguments.contains("--ui-testing") ? "light" : UserDefaults.standard.string(forKey: "companionAppearance") ?? "system"
    var notice: String?
    var noticeSequence = 0
    var persistentNotice = true
    func notify(_ text: String, persistent: Bool = true) { noticeSequence += 1; notice = text; persistentNotice = persistent }
    var share: SharedNote?
    var selectedID: UUID?
    var selectedPassage: MemoryPassage?
    var selectedAttachment: CompanionAttachment? { sessions.first(where: { $0.id == selectedID }).flatMap { recording.companionAttachment(for: $0) } }
    func refreshSelected() { if let session = sessions.first(where: { $0.id == selectedID }) { loadNote(session) } }
    var draftVersion = 0
    var foreground = true
    private let tapFeedback = UIImpactFeedbackGenerator(style: .light)
    private var needsRefresh = false
    private var notes: [String: RecordingNotesResult] = [:]
    private var notesErrors: [String: String] = [:]
    private struct NotesTask { let id: UUID; let task: Task<Void, Never> }
    private var notesTasks: [String: NotesTask] = [:]
    private var libraryTask: Task<Void, Never>?
    struct SharedNote: Identifiable { let id = UUID(); let text: String }

    static func config() throws -> RelayConfiguration {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if args.contains("--ui-testing"), args.contains("--companion-ui-fixture") {
            let raw = ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"] ?? ""
            let config = try JSONDecoder().decode(RelayConfiguration.self, from: Data(raw.utf8))
            guard config.url.scheme == "ws", config.url.host == "127.0.0.1", config.memoryOwnerID != nil else { throw CaptureFailure.noRelay }
            return config
        }
        #endif
        return try RelayConfiguration.load()
    }
    func start() {
        guard chat == nil else { return }
        do {
            let config = try Self.config()
            guard let owner = config.memoryOwnerID else { throw CaptureFailure.noRelay }
            chat = CompanionController(owner: owner, makeConnection: {
                CompanionSocketConnection(configuration: {
                    let config = try Self.config()
                    guard config.memoryOwnerID == owner else { throw AskFailure.accessExpired }
                    return config
                })
            })
            #if DEBUG
            let args = ProcessInfo.processInfo.arguments
            if (args.contains("--proactive-qa") && config.url.host == "127.0.0.1") || args.contains("--proactive-phone-qa") {
                proactive = ProactiveCoordinator(makeConnection: {
                    ProactiveSocketConnection(configuration: {
                        let config = try Self.config()
                        guard config.memoryOwnerID == owner else { throw AskFailure.accessExpired }
                        return config
                    })
                }, received: { [weak self] in self?.needsRefresh = true; self?.refreshIfReady() })
            }
            #endif
            if !recording.pendingMemoryDeletion { chat?.refresh() }
        } catch { notify(error.localizedDescription) }
    }
    var sessions: [CaptureSession] {
        var values = recording.sessions
        if recording.isActive, let current = recording.current {
            values.removeAll { $0.id == current.id }; values.insert(current, at: 0)
        }
        return values
    }
    var proactiveSource: MemorySource? {
        guard recording.liveStatus == "Recording", let current = recording.current, current.memoryOwnerID == chat?.owner else { return nil }
        return MemorySource(live: current, revision: 1, finalizedOnly: true)
    }
    func updateProactive() {
        guard chat?.useMemory == true else { proactive?.quiet(); return }
        proactive?.update(proactiveSource, foreground: foreground && !recording.pendingMemoryDeletion && !SharedMicrophone.shared.meetingAudioPaused)
    }
    func refreshIfReady() {
        guard needsRefresh, let chat, !chat.isBusy, !recording.pendingMemoryDeletion else { return }
        needsRefresh = false; chat.refresh()
    }
    func scene(_ phase: ScenePhase) {
        foreground = phase == .active
        if !foreground { proactive?.suspend() }
        if phase == .background {
            dictation.interrupt(); recording.didEnterBackground(); chat?.didEnterBackground()
            libraryTask?.cancel(); notesTasks.values.forEach { $0.task.cancel() }; notesTasks.removeAll()
        } else if phase == .active { recording.didBecomeActive(); chat?.didBecomeActive(); updateProactive(); refreshSelected() }
    }
    private func key(_ attachment: CompanionAttachment) -> String { "\(chat?.owner ?? ""):\(attachment.session_id):\(attachment.revision)" }
    private func result(_ session: CaptureSession) -> RecordingNotesResult? {
        guard let a = recording.companionAttachment(for: session) else { return nil }; return notes[key(a)]
    }
    private func title(_ session: CaptureSession) -> String {
        result(session)?.notes?.title ?? (session.source == "personal_text" ? "Personal note" : "Recorded conversation")
    }
    private func export(_ session: CaptureSession) -> String {
        title(session) + "\n\n" + session.transcript.segments.map(\.text).joined(separator: "\n")
    }
    private func cacheKey(_ session: CaptureSession, _ attachment: CompanionAttachment) -> RecordingNotesCache.Key? {
        guard let owner = chat?.owner, session.memoryOwnerID == owner else { return nil }
        return .init(owner: owner, sessionID: attachment.session_id, revision: attachment.revision)
    }
    private func hydrateNote(_ session: CaptureSession) {
        guard let a = recording.companionAttachment(for: session), let identity = cacheKey(session, a) else { return }
        do {
            if let saved = try RecordingNotesCache.shared.read(identity) { notes[key(a)] = saved }
        } catch { notesErrors[key(a)] = "Saved notes couldn’t load. Trying to refresh them." }
    }
    private func refreshNote(_ session: CaptureSession, retry: Bool = false) async throws -> RecordingNotesResult? {
        guard let a = recording.companionAttachment(for: session), let identity = cacheKey(session, a) else { return nil }
        let k = key(a)
        func stillCurrent() -> Bool {
            chat?.owner == identity.owner && (try? Self.config().memoryOwnerID) == identity.owner && sessions.contains {
                $0.id == session.id && recording.companionAttachment(for: $0)?.revision == identity.revision
            }
        }
        do {
            let value = try await RecordingNotesCache.shared.refresh(identity, retry: retry) {
                try await RecordingNotesConnection(configuration: {
                    let config = try Self.config()
                    guard config.memoryOwnerID == identity.owner else { throw AskFailure.accessExpired }
                    return config
                }).read(a, retry: retry)
            }
            try Task.checkCancellation()
            guard stillCurrent() else { return nil }
            // A pending or failed regeneration must not blank the last ready summary.
            if let saved = try RecordingNotesCache.shared.read(identity) { notes[k] = saved }
            else { notes[k] = value }
            notesErrors[k] = nil
            return value
        } catch {
            guard !Task.isCancelled, stillCurrent() else { throw CancellationError() }
            if let source = error as? RecordingNotesSourceFailure {
                notes[k] = nil
                notesErrors[k] = source.reason == .unavailable
                    ? "This recording is no longer available."
                    : "The transcript changed. These notes are no longer current."
                if source.cacheRemovalFailed { notesErrors[k, default: ""] += " Saved notes couldn’t be removed from this device." }
            } else { notesErrors[k] = "Notes couldn’t refresh. Your saved notes and transcript are still available." }
            throw error
        }
    }
    private func loadNote(_ session: CaptureSession, retry: Bool = false) {
        hydrateNote(session)
        guard let a = recording.companionAttachment(for: session) else { return }
        let k = key(a); guard notesTasks[k] == nil else { return }
        let id = UUID()
        let task = Task { [weak self] in
            guard let self else { return }
            defer { if self.notesTasks[k]?.id == id { self.notesTasks[k] = nil } }
            do {
                for poll in 0..<10 {
                    let value = try await self.refreshNote(session, retry: retry && poll == 0)
                    if value?.state != "pending" && value?.state != "generating" { return }
                    try await Task.sleep(for: .seconds(2))
                }
            } catch {
                if !Task.isCancelled, self.selectedID == session.id, self.notes[k]?.state == "ready", let message = self.notesErrors[k] {
                    self.notify(message)
                }
            }
        }
        notesTasks[k] = NotesTask(id: id, task: task)
    }
    func loadLibrary() {
        libraryTask?.cancel()
        // Hydrate every title before the first network suspension, including offline launches.
        sessions.forEach(hydrateNote)
        libraryTask = Task { [weak self] in
            guard let self else { return }
            // Read-only, sequential revalidation. No generation/retry commands.
            for session in self.sessions {
                if Task.isCancelled { return }
                do { _ = try await self.refreshNote(session) }
                catch { if Task.isCancelled { return } }
            }
        }
    }
    func action(_ command: [String: Any]) {
        guard let action = command["action"] as? String else { return }
        let id = (command["id"] as? String).flatMap(UUID.init(uuidString:))
        let session = sessions.first { $0.id == id }
        switch action {
        case "prepare-haptic": if foreground { tapFeedback.prepare() }
        case "haptic":
            if foreground { tapFeedback.impactOccurred(intensity: 0.8); tapFeedback.prepare() }
        case "draft":
            guard let text = command["text"] as? String, text.utf8.count <= 32000,
                  let revision = command["revision"] as? Int, revision >= draftVersion, !dictation.isActive else { return }
            draftVersion = revision; chat?.draft = text
        case "send":
            guard let chat, !chat.isBusy, !dictation.isActive, !recording.pendingMemoryDeletion,
                  let text = command["text"] as? String, text.utf8.count <= 32000 else { return }
            draftVersion = max(draftVersion, command["revision"] as? Int ?? 0)
            chat.draft = text; chat.send(live: recording.liveStatus == "Recording" ? recording.current : nil)
        case "start":
            guard foreground, !recording.isActive, !dictation.isActive else { return }
            recording.startRecording()
        case "stop": if recording.liveStatus == "Recording" { recording.stop() }
        case "quiet": proactive?.quiet()
        case "cancel": chat?.cancel()
        case "recover": if !recording.pendingMemoryDeletion { chat?.recoverUncertainResponse() }
        case "refresh": if !recording.pendingMemoryDeletion { chat?.refresh(userInitiated: true) }
        case "earlier": if !recording.pendingMemoryDeletion { chat?.loadEarlier() }
        case "dictate":
            guard foreground, let chat, !chat.isBusy, !recording.pendingMemoryDeletion else { return }
            dictation.start { [weak self] text, send in
                guard let self else { return }
                chat.draft = ComposerDictation.appending(text, to: chat.draft)
                if send, self.foreground, !chat.isBusy, !self.recording.pendingMemoryDeletion {
                    chat.send(live: self.recording.liveStatus == "Recording" ? self.recording.current : nil)
                }
            }
        case "send-dictation": dictation.finish(send: true)
        case "discard-dictation": dictation.discard()
        case "interrupt-dictation": dictation.interrupt()
        case "attach": if let session, let a = recording.companionAttachment(for: session) { chat?.attachment = a }
        case "detach": chat?.attachment = nil
        case "library": loadLibrary()
        case "open-note": if let session { selectedPassage = nil; selectedID = session.id; loadNote(session) }
        case "passage":
            if let session, let a = recording.companionAttachment(for: session), let passage = command["passage"] as? String {
                selectedPassage = MemorySource(session, revision: a.revision).passages.first { $0.id == passage }
            }
        case "refresh-note", "retry-note": if let session { loadNote(session, retry: action == "retry-note") }
        case "close-note": selectedID = nil; selectedPassage = nil
        case "delete":
            if let session, recording.deleteFromLibrary(session) {
                let prefix = "\(chat?.owner ?? ""):\(session.id.uuidString):"
                for (k, work) in notesTasks where k.hasPrefix(prefix) { work.task.cancel(); notesTasks[k] = nil }
                notes = notes.filter { !$0.key.hasPrefix(prefix) }; notesErrors = notesErrors.filter { !$0.key.hasPrefix(prefix) }
                if chat?.attachment?.session_id == session.id.uuidString { chat?.attachment = nil }
                selectedID = nil; needsRefresh = true; refreshIfReady()
            }
        case "copy-note": if let session { ExperienceClipboard.copy(export(session)); notify("Note copied.", persistent: false) }
        case "share-note": if let session { share = SharedNote(text: export(session)) }
        case "copy-message":
            if let id = command["id"] as? String, let message = messages.first(where: { $0["id"] as? String == id }), let text = message["text"] as? String { ExperienceClipboard.copy(text); notify("Copied.", persistent: false) }
            else if command["id"] as? String == "welcome" { ExperienceClipboard.copy("Hey, good to see you.") }
            else if command["id"] as? String == "welcome-2" { ExperienceClipboard.copy("What’s on your mind?") }
        case "appearance":
            if let value = command["value"] as? String, ["system", "light", "dark"].contains(value) { appearance = value; if !ProcessInfo.processInfo.arguments.contains("--ui-testing") { UserDefaults.standard.set(value, forKey: "companionAppearance") } }
        case "memory": if let value = command["value"] as? Bool { chat?.useMemory = value; updateProactive() }
        default: break
        }
    }
    private var messages: [[String: Any]] {
        var output: [[String: Any]] = []
        for turn in chat?.turns ?? [] {
            if !turn.isProactive { output.append(["id": turn.id + "-q", "text": turn.question, "user": true]) }
            for (index, text) in CompanionMessageText.bubbles(turn.answer ?? "", proactive: turn.isProactive).enumerated() where !text.isEmpty {
                output.append(["id": turn.id + "-a-\(index)", "text": text, "user": false])
            }
        }
        if let response = chat?.response {
            output.append(["id": response.request.question_id + "-q", "text": response.request.question, "user": true])
            let text = CompanionMessageText.presented(response.text, streaming: response.state == .streaming)
            if !text.isEmpty { output.append(["id": response.request.question_id + "-a-0", "text": text, "user": false]) }
        }
        return output
    }
    var snapshot: [String: Any] {
        var state: [String: Any] = ["ready": chat != nil, "busy": chat?.isBusy ?? false, "deleting": recording.pendingMemoryDeletion,
            "draft": chat?.draft ?? "", "draftVersion": draftVersion, "appearance": appearance, "useMemory": chat?.useMemory ?? true,
            "messages": messages, "hasEarlier": chat?.nextBefore != nil, "showWelcome": chat?.nextBefore == nil,
            "uncertain": chat?.response?.state == .uncertain, "notice": notice ?? "", "noticeSequence": noticeSequence, "persistentNotice": persistentNotice]
        state["notes"] = sessions.map { session -> [String: Any] in
            let day = Calendar.current.isDateInToday(session.createdAt) ? "Today" : Calendar.current.isDateInYesterday(session.createdAt) ? "Yesterday" : session.createdAt.formatted(date: .abbreviated, time: .omitted)
            let full = session.transcript.segments.map(\.text).joined(separator: " ")
            return ["id": session.id.uuidString, "title": title(session), "preview": String(full.prefix(240)), "search": full,
                "day": day, "metadata": session.createdAt.formatted(date: .omitted, time: .shortened) + (session.recordingSeconds.map { " · \(Int($0 / 60)) min" } ?? ""),
                "active": recording.isActive && recording.current?.id == session.id, "attachable": recording.companionAttachment(for: session) != nil, "personal": session.source == "personal_text"]
        }
        if let attachment = chat?.attachment, let session = sessions.first(where: { $0.id.uuidString == attachment.session_id }) {
            state["attachment"] = ["id": session.id.uuidString, "title": title(session)]
        }
        if let status = recording.liveStatus, let current = recording.current {
            state["capture"] = ["id": current.id.uuidString, "label": SharedMicrophone.shared.meetingAudioPaused ? "Paused for dictation" : status == "Recording" ? "Listening" : status,
                "time": Self.clock(Int(recording.elapsedRecordingSeconds)), "canStop": status == "Recording", "quiet": proactive?.isQuiet ?? false,
                "canQuiet": proactive != nil && proactive?.isQuiet == false]
        }
        if dictation.isActive {
            state["dictation"] = ["status": String(describing: dictation.state), "time": Self.clock(dictation.elapsedSeconds), "levels": dictation.levels]
        }
        if let session = sessions.first(where: { $0.id == selectedID }) {
            var detail: [String: Any] = ["id": session.id.uuidString]
            if let selectedPassage { detail["passage"] = ["label": "Supporting passage · " + Self.clock(Int(selectedPassage.start)), "text": selectedPassage.text] }
            detail["transcript"] = session.transcript.segments.flatMap { segment in segment.speakerTurns.map { turn in
                ["label": Self.clock(Int(segment.start)) + " · " + (turn.speaker.map { "Speaker \($0 + 1)" } ?? "Speaker unknown"), "text": turn.text]
            } }
            if let result = result(session), result.state == "ready", let notes = result.notes {
                var paragraphs: [[String: Any]] = [["heading": "Overview"], ["text": notes.overview.text, "passages": notes.overview.passages]]
                for section in notes.sections {
                    paragraphs.append(["heading": section.heading]);paragraphs += section.items.map { ["text": $0.text, "passages": $0.passages] }
                }; detail["notes"] = paragraphs
            } else if let a = recording.companionAttachment(for: session) {
                let result = notes[key(a)]
                detail["status"] = notesErrors[key(a)] ?? (result?.state == "failed" ? "Notes couldn’t be prepared. Your transcript is still available." : "Preparing notes…")
                detail["retryable"] = result?.state == "failed" && !["empty_transcript", "notes_input_too_large"].contains(result?.error ?? "")
            } else { detail["status"] = "Notes become available after this recording syncs." }
            state["detail"] = detail
        }
        return state
    }
    private static func clock(_ seconds: Int) -> String { String(format: "%d:%02d", seconds / 60, seconds % 60) }
}

struct SharedRoomRootView: View {
    @State private var model = RoomWebModel()
    @State private var interfaceFailure: String?
    @State private var interfaceVersion = 0
    @Environment(\.scenePhase) private var scenePhase
    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { _ in
            RoomWebView(state: model.snapshot, onAction: model.action, onFailure: { interfaceFailure = $0 })
                .id(interfaceVersion)
        }.background(Color(UIColor { traits in
            traits.userInterfaceStyle == .dark ? UIColor(red: 21/255, green: 24/255, blue: 25/255, alpha: 1) : .white
        }))
            .preferredColorScheme(model.appearance == "system" ? nil : model.appearance == "dark" ? .dark : .light)
            .task { model.start() }
            .onChange(of: model.chat?.notice) { _, text in if let text { model.notify(text) } }
            .onChange(of: model.recording.errorMessage) { _, text in if let text { model.notify(text) } }
            .onChange(of: model.dictation.notice) { _, text in if let text { model.notify(text) } }
            .onChange(of: model.chat?.refreshStatus) { _, text in if let text { model.notify(text, persistent: false) } }
            .onChange(of: scenePhase) { _, phase in model.scene(phase) }
            .onChange(of: model.selectedAttachment) { _, _ in model.refreshSelected() }
            .onChange(of: model.proactiveSource) { _, _ in model.updateProactive() }
            .onChange(of: model.chat?.isBusy) { _, _ in model.refreshIfReady() }
            .onChange(of: SharedMicrophone.shared.meetingAudioPaused) { _, _ in model.updateProactive() }
            .onChange(of: model.recording.pendingMemoryDeletion) { _, pending in
                if pending { model.dictation.interrupt(); model.proactive?.suspend(); model.notify("Removing the source. Chat will resume when synchronization finishes.") }
                else { model.chat?.refresh(); model.updateProactive() }
            }
            .onChange(of: model.recording.isActive) { _, active in if !active { model.loadLibrary() } }
            .sheet(item: $model.share) { note in RoomShareSheet(text: note.text) }
            // A broken web process cannot render its own error. Keep recovery outside that process.
            .alert("Couldn’t display the interface", isPresented: Binding(get: { interfaceFailure != nil }, set: { if !$0 { interfaceFailure = nil } })) {
                Button("Reload interface") { interfaceFailure = nil; interfaceVersion += 1 }
            } message: { Text(interfaceFailure ?? "Your saved conversations are safe.") }
    }
}
private struct RoomShareSheet: UIViewControllerRepresentable {
    let text: String
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: [text], applicationActivities: nil) }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}
#endif
