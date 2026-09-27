import SwiftUI

struct ConversationAskView: View {
    let controller: SessionController
    let answers: [ConversationAnswer]
    @State private var question = ""
    @State private var source: ConversationPassage?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Divider()
            Text("Ask about this conversation").font(.headline)
            Text("Answers use the supplied conversation context. Each question stands on its own.")
                .font(.caption).foregroundStyle(.secondary)
            if controller.liveStatus == "Recording" {
                Text("Recording continues while you ask. Recent speech may still be processing; Ask uses only the transcript received so far.")
                    .font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("liveAskNotice")
            }
            if let error = controller.answerErrorMessage {
                Text(error).foregroundStyle(.red).accessibilityIdentifier("answerError")
            }
            ForEach(answers) { answer in
                VStack(alignment: .leading, spacing: 8) {
                    Text(answer.question.question).font(.headline)
                    if let cutoff = answer.transcriptCutoffSeconds {
                        Text(String(format: "Transcript snapshot through %.1fs", cutoff))
                            .font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("answerCutoff")
                    }
                    if answer.capturedWhileRecording == true {
                        Text("Later speech is not included in this answer.").font(.caption).foregroundStyle(.secondary)
                    }
                    if answer.includedInterimText == true {
                        Text("This snapshot includes provisional text. Its saved sources stay fixed if the transcript changes.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Text(answer.text.isEmpty ? (answer.state == .streaming ? "Thinking…" : "No answer text received.") : CompanionMessageText.presented(answer.text, streaming: answer.state == .streaming))
                        .textSelection(.enabled).accessibilityIdentifier("answerText")
                    if answer.state == .streaming {
                        Text("Answering…").font(.caption).foregroundStyle(.secondary)
                    }
                    if let notice = answer.notice {
                        Text(notice).font(.caption).foregroundStyle(.secondary)
                    }
                    if answer.state == .completed, CompanionMessageText.showsEvidence {
                        ForEach(answer.references, id: \.self) { reference in
                            if let passage = (answer.question.passages + (answer.pastSources ?? [])).first(where: { $0.id == reference }) {
                                if passage.retained_claim_id != nil {
                                    Text("Memory \(reference) · recording deleted")
                                        .font(.caption).foregroundStyle(.secondary)
                                        .accessibilityIdentifier("retainedMemoryReference")
                                } else {
                                    Button(String(format: passage.session_id == nil ? "Source %@ · %.1fs" : "Past source %@ · %.1fs", reference, passage.start)) { source = passage }
                                        .accessibilityIdentifier("answerSource")
                                }
                            }
                        }
                    }
                }
            }
            TextField("What would you like to know?", text: $question, axis: .vertical)
                .textFieldStyle(.roundedBorder).lineLimit(1...4)
                .disabled(controller.isAnswering).accessibilityIdentifier("askQuestion")
            if controller.isAnswering {
                Button("Cancel answer") { controller.cancelAnswer() }.accessibilityIdentifier("cancelAnswer")
            } else {
                Button("Ask") { controller.ask(question) }
                    .disabled(!controller.canAsk || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .accessibilityIdentifier("submitQuestion")
            }
        }
        .sheet(item: $source) { passage in
            VStack(alignment: .leading, spacing: 16) {
                Text(String(format: "Transcript source · %.1fs", passage.start)).font(.headline)
                if let timestamp = passage.captured_at {
                    Text("Previous conversation · " + Date(timeIntervalSince1970: timestamp).formatted(date: .abbreviated, time: .shortened))
                        .font(.caption).accessibilityIdentifier("pastSourceDate")
                }
                ScrollView { Text(passage.text).textSelection(.enabled) }
                Text("Captured with this answer. Speaker identity is not verified.").font(.caption).foregroundStyle(.secondary)
                Button("Done") { source = nil }
            }.padding(24).frame(minWidth: 280, minHeight: 240)
        }
    }
}
