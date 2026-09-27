import SwiftUI

/// Notes are derived from one exact terminal transcript revision.
struct RecordingNotesView: View {
    let attachment: CompanionAttachment
    let configuration: () throws -> RelayConfiguration
    let onPassage: (String) -> Void
    @State private var result: RecordingNotesResult?
    @State private var loading = true
    @State private var unavailable = false
    @State private var refresh = 0
    @State private var retry = false
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if let result, result.state == "ready", let notes = result.notes {
                Text(notes.title).font(.title2.bold()).accessibilityIdentifier("notesTitle")
                if result.incomplete { Text("Notes from an incomplete recording").font(.caption) }
                bullet(notes.overview)
                ForEach(Array(notes.sections.enumerated()), id: \.offset) { _, section in
                    Text(section.heading).font(.headline)
                    ForEach(Array(section.items.enumerated()), id: \.offset) { _, item in bullet(item) }
                }
                Text("Generated from this transcript. Check the supporting passages for details.").font(.caption).foregroundStyle(.secondary)
            } else if loading {
                ExperienceThinkingStatus(label: "Preparing notes…").accessibilityIdentifier("notesLoading")
            } else {
                Text(status).foregroundStyle(.secondary).accessibilityIdentifier("notesStatus")
                if result?.state == "failed", !["empty_transcript", "notes_input_too_large"].contains(result?.error ?? "") {
                    Button("Retry notes") { retry = true; refresh += 1 }.accessibilityIdentifier("retryNotes")
                }
                Button("Refresh notes") { refresh += 1 }.accessibilityIdentifier("refreshNotes")
            }
        }
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
                    if value?.state == "ready" { return }
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
        VStack(alignment: .leading, spacing: 6) {
            Text(item.text).textSelection(.enabled).accessibilityIdentifier("notesText")
            ScrollView(.horizontal) { HStack {
                ForEach(item.passages, id: \.self) { passage in
                    Button("Passage \(passage.dropFirst())") { onPassage(passage) }
                        .font(.caption).frame(minHeight: 44).accessibilityIdentifier("notesPassage")
                }
            } }
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
