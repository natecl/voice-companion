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
            Text("Answers use this transcript. Each question stands on its own.")
                .font(.caption).foregroundStyle(.secondary)
            ForEach(answers) { answer in
                VStack(alignment: .leading, spacing: 8) {
                    Text(answer.question.question).font(.headline)
                    Text(answer.text.isEmpty ? (answer.state == .streaming ? "Thinking…" : "No answer text received.") : answer.text)
                        .textSelection(.enabled).accessibilityIdentifier("answerText")
                    if answer.state == .streaming {
                        Text("Answering… · sources checked when complete").font(.caption).foregroundStyle(.secondary)
                    }
                    if let notice = answer.notice {
                        Text(notice).font(.caption).foregroundStyle(.secondary)
                    }
                    if answer.state == .completed {
                        ForEach(answer.references, id: \.self) { reference in
                            if let passage = answer.question.passages.first(where: { $0.id == reference }) {
                                Button(String(format: "Source %@ · %.1fs", reference, passage.start)) { source = passage }
                                    .accessibilityIdentifier("answerSource")
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
                    .disabled(question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .accessibilityIdentifier("submitQuestion")
            }
        }
        .sheet(item: $source) { passage in
            VStack(alignment: .leading, spacing: 16) {
                Text(String(format: "Transcript source · %.1fs", passage.start)).font(.headline)
                ScrollView { Text(passage.text).textSelection(.enabled) }
                Text("Captured with this answer. Speaker identity is not verified.").font(.caption).foregroundStyle(.secondary)
                Button("Done") { source = nil }
            }.padding(24).frame(minWidth: 280, minHeight: 240)
        }
    }
}
