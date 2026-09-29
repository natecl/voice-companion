import SwiftUI

/// Notes are derived from one exact terminal transcript revision.
struct RecordingNotesView: View {
    let attachment: CompanionAttachment
    let configuration: () throws -> RelayConfiguration
    let onPassage: (String) -> Void
    var onTitle: (String) -> Void = { _ in }
    @State private var result: RecordingNotesResult?
    @State private var loading = true
    @State private var unavailable = false
    @State private var refresh = 0
    @State private var retry = false
    @State private var displayedKey: RecordingNotesCache.Key?
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            if let result, result.state == "ready", let notes = result.notes {
                if result.incomplete { Text("Notes from an incomplete recording").font(.caption) }
                VStack(alignment: .leading, spacing: 16) {
                Text("Overview").font(.system(.title2, design: .serif, weight: .bold))
                paragraph(notes.overview)
                ForEach(Array(notes.sections.enumerated()), id: \.offset) { _, section in
                    Divider().padding(.vertical, 3)
                    Text(section.heading).font(.headline)
                    ForEach(Array(section.items.enumerated()), id: \.offset) { _, item in paragraph(item, bulleted: true) }
                }
                }.padding(18).frame(maxWidth: .infinity, alignment: .leading).experienceCard(radius: 15)
                Text("Generated from this transcript. Long-press a paragraph to view its supporting transcript.").font(.caption).foregroundStyle(ExperienceStyle.secondary)
                if unavailable {
                    Text("Showing saved notes. Refresh couldn’t finish.").font(.caption).accessibilityIdentifier("notesRefreshStatus")
                    Button("Refresh notes") { refresh += 1 }.accessibilityIdentifier("refreshNotes")
                }
            } else if loading {
                ExperienceThinkingStatus(label: "Preparing notes…").accessibilityIdentifier("notesLoading")
            } else {
                Text(status).foregroundStyle(ExperienceStyle.secondary).accessibilityIdentifier("notesStatus")
                if result?.state == "failed", !["empty_transcript", "notes_input_too_large"].contains(result?.error ?? "") {
                    Button("Retry notes") { retry = true; refresh += 1 }.accessibilityIdentifier("retryNotes")
                }
                Button("Refresh notes") { refresh += 1 }.accessibilityIdentifier("refreshNotes")
            }
        }
        .font(.callout)
        .task(id: "\(attachment.session_id):\(attachment.revision):\(refresh):\(scenePhase)") {
            guard scenePhase == .active else { return }
            let shouldRetry = retry; retry = false
            unavailable = false
            defer { loading = false }
            do {
                let config = try configuration()
                guard let owner = config.memoryOwnerID else { throw CompanionFailure.sourceUnavailable }
                let key = RecordingNotesCache.Key(owner: owner, sessionID: attachment.session_id, revision: attachment.revision)
                if displayedKey != key { result = nil; displayedKey = key }
                if let saved = try? RecordingNotesCache.shared.read(key) { result = saved; if let title = saved.notes?.title { onTitle(title) } }
                loading = result == nil
                let connection = RecordingNotesConnection(configuration: {
                    let current = try configuration()
                    guard current.memoryOwnerID == owner else { throw CompanionFailure.sourceUnavailable }
                    return current
                })
                for poll in 0..<10 {
                    let value = try await RecordingNotesCache.shared.refresh(key, retry: shouldRetry && poll == 0) {
                        try await connection.read(attachment, retry: shouldRetry && poll == 0)
                    }
                    try Task.checkCancellation()
                    guard try configuration().memoryOwnerID == owner else { result = nil; throw CompanionFailure.sourceUnavailable }
                    if value?.state == "ready" {
                        result = value
                        if let title = value?.notes?.title { onTitle(title) }
                        return
                    }
                    // Pending/failed refreshes do not replace a usable saved summary.
                    let saved = try RecordingNotesCache.shared.read(key)
                    result = saved ?? value
                    if saved == nil { onTitle("Recorded conversation") }
                    if value?.state != "pending" && value?.state != "generating" { unavailable = saved != nil; return }
                    if poll < 9 { try await Task.sleep(for: .seconds(2)) }
                }
            } catch {
                if !Task.isCancelled {
                    if (try? configuration().memoryOwnerID) != displayedKey?.owner { result = nil }
                    unavailable = true
                }
            }
        }
    }
    private var status: String {
        if unavailable { return "Notes couldn’t be loaded. Your transcript is still available." }
        switch result?.state {
        case "pending", "generating": return "Notes are still being prepared. You can return later."
        case "outdated": return "The transcript changed. These notes are no longer current."
        case "failed":
            switch result?.error {
            case "empty_transcript": return "There isn’t any finalized text to summarize."
            case "notes_input_too_large": return "This transcript is too long for notes in this version."
            case "budget_limit": return "The notes generation allowance has been reached. Your transcript is saved."
            default: return "Notes didn’t finish. Your transcript is saved."
            }
        default: return "No notes have been generated for this recording."
        }
    }
    private func paragraph(_ item: RecordingNotes.Bullet, bulleted: Bool = false) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            if bulleted { Text("•").foregroundStyle(ExperienceStyle.secondary) }
            Text(item.text)
                .font(.body.weight(.regular))
                .lineSpacing(4)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
                .accessibilityIdentifier("notesText")
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
        .contextMenu {
            ForEach(item.passages, id: \.self) { passage in
                Button("View passage \(passage.dropFirst())") { onPassage(passage) }
                    .accessibilityIdentifier("notesPassage")
            }
        }
    }

}

/// A library read never schedules generation; fallback remains usable offline.
struct RecordingLibraryTitle: View {
    let attachment: CompanionAttachment?
    let personal: Bool
    var refreshKey = ""
    let configuration: () throws -> RelayConfiguration
    @State private var title: String?
    var body: some View {
        Text(title ?? (personal ? "Personal note" : "Recorded conversation"))
            .task(id: "\(attachment?.session_id ?? ""): \(attachment?.revision ?? 0):\(refreshKey)") {
                title = nil
                guard !personal, let attachment else { return }
                do {
                    let config = try configuration()
                    guard let owner = config.memoryOwnerID else { return }
                    let key = RecordingNotesCache.Key(owner: owner, sessionID: attachment.session_id, revision: attachment.revision)
                    if let saved = try? RecordingNotesCache.shared.read(key) { title = saved.notes?.title }
                    let result = try await RecordingNotesCache.shared.refresh(key) {
                        try await RecordingNotesConnection(configuration: {
                            let current = try configuration()
                            guard current.memoryOwnerID == owner else { throw CompanionFailure.sourceUnavailable }
                            return current
                        }).read(attachment)
                    }
                    try Task.checkCancellation()
                    guard try configuration().memoryOwnerID == owner else { title = nil; return }
                    title = (try RecordingNotesCache.shared.read(key))?.notes?.title
                    if result?.state == "ready" { title = result?.notes?.title }
                } catch { /* The generic title remains available offline. */ }
            }
    }
}
