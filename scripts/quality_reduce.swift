import Foundation

/// Build together with App/Transcription/Transcript.swift: score exactly what the app retains.
@main
enum QualityReduce {
    static func main() throws {
        let events = try JSONDecoder().decode([ReplayEvent].self,
            from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var transcript = Transcript()
        for item in events { if let segment = item.event.segment { transcript.apply(segment) } }
        FileHandle.standardOutput.write(try JSONEncoder().encode(transcript))
    }
}
