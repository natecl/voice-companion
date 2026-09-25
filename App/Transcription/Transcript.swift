import Foundation

struct TranscriptWord: Codable, Equatable {
    let text: String
    let start: Double
    let end: Double
    let speaker: Int?
}

struct TranscriptSegment: Codable, Identifiable {
    var id: Double { start }
    let start: Double
    let duration: Double
    let text: String
    let words: [TranscriptWord]
    let isFinal: Bool
}

struct Transcript: Codable {
    var segments: [TranscriptSegment] = []
    var receivedThroughSeconds: Double {
        segments.map { $0.start + $0.duration }.max() ?? 0
    }

    mutating func apply(_ segment: TranscriptSegment) {
        guard !segment.text.isEmpty else { return }
        // A stitched utterance replaces all overlapping interim/chunk results.
        let end = segment.start + segment.duration
        segments.removeAll {
            abs($0.start - segment.start) < 0.02 ||
            ($0.start < end - 0.001 && $0.start + $0.duration > segment.start + 0.001)
        }
        segments.append(segment)
        segments.sort { $0.start < $1.start }
    }
}

struct GrokEvent: Decodable {
    let type: String
    let text: String?
    let words: [TranscriptWord]?
    let start: Double?
    let duration: Double?
    let is_final: Bool?
    var message: String? = nil

    var segment: TranscriptSegment? {
        guard type == "transcript.partial", let text, !text.isEmpty,
              let start, let duration else { return nil }
        return TranscriptSegment(start: start, duration: duration, text: text,
                                 words: words ?? [], isFinal: is_final ?? false)
    }
}

struct ReplayEvent: Decodable {
    let elapsed: Double
    let event: GrokEvent
}
