import Foundation

/// Grounding tags stay in stored/protocol text; the conversation displays only the message.
enum CompanionMessageText {
    static var showsEvidence: Bool {
        #if DEBUG
        ProcessInfo.processInfo.arguments.contains("--show-evidence-debug")
        #else
        false
        #endif
    }

    static func display(_ text: String, streaming: Bool = false) -> String {
        var result = text.replacingOccurrences(of: #"[ \t]*\[\[[pm][0-9]+\]\]"#, with: "", options: .regularExpression)
        if streaming {
            // Never flash a citation while its delimiters/ID are arriving across deltas.
            result = result.replacingOccurrences(of: #"[ \t]*\[{1,2}(?:[pm][0-9]*\]?)?$"#, with: "", options: .regularExpression)
        }
        // An interrupted answer can be saved halfway through an internal tag.
        result = result.replacingOccurrences(of: #"[ \t]*\[\[[pm][0-9]*\]?$"#, with: "", options: .regularExpression)
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func presented(_ text: String, streaming: Bool = false) -> String {
        showsEvidence ? text : display(text, streaming: streaming)
    }
}
