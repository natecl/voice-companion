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
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            if let result, result.state == "ready", let notes = result.notes {
                if result.incomplete { Text("Notes from an incomplete recording").font(.caption) }
                VStack(alignment: .leading, spacing: 16) {
                Text("Overview").font(.system(.title2, design: .serif, weight: .bold))
                bullet(notes.overview)
                ForEach(Array(notes.sections.enumerated()), id: \.offset) { _, section in
                    Divider().padding(.vertical, 3)
                    Text(section.heading).font(.headline)
                    ForEach(Array(section.items.enumerated()), id: \.offset) { _, item in bullet(item) }
                }
                }.padding(18).frame(maxWidth: .infinity, alignment: .leading).experienceCard(radius: 15)
                Label("Notes ready", systemImage: "checkmark").font(.callout).foregroundStyle(.green)
                Text("Generated from this transcript. Check the supporting passages for details.").font(.caption).foregroundStyle(ExperienceStyle.secondary)
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
            result = nil; unavailable = false; loading = true
            let shouldRetry = retry; retry = false
            defer { loading = false }
            do {
                let connection = RecordingNotesConnection(configuration: configuration)
                for poll in 0..<10 {
                    let value = try await connection.read(attachment, retry: shouldRetry && poll == 0)
                    try Task.checkCancellation()
                    result = value
                    if value?.state == "ready" { if let title = value?.notes?.title { onTitle(title) }; return }
                    if value?.state != "pending" && value?.state != "generating" { return }
                    if poll < 9 { try await Task.sleep(for: .seconds(2)) }
                }
            } catch { if !Task.isCancelled { result = nil; unavailable = true } }
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
    private func bullet(_ item: RecordingNotes.Bullet) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Text(item.text).textSelection(.enabled).accessibilityIdentifier("notesText").frame(maxWidth: .infinity, alignment: .leading)
            ForEach(item.passages, id: \.self) { passage in
                Button { onPassage(passage) } label: {
                    ExperienceSymbol(name: "doc.text").frame(width: 12, height: 14).foregroundStyle(ExperienceStyle.secondary).frame(width: 44, height: 44)
                }.accessibilityLabel("Supporting passage \(passage.dropFirst())").accessibilityIdentifier("notesPassage")
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
                    let result = try await RecordingNotesConnection(configuration: configuration).read(attachment)
                    try Task.checkCancellation()
                    if result?.state == "ready" { title = result?.notes?.title }
                } catch { /* The generic title remains available offline. */ }
            }
    }
}
