import Foundation

struct GoogleAccountGrant: Codable, Sendable, Equatable {
    let subject: String
    let token: String

    func validate() throws {
        guard !subject.isEmpty, subject.utf8.count <= 255,
              !token.isEmpty, token.utf8.count <= 8192,
              !subject.contains(where: { $0.isWhitespace }), !token.contains(where: { $0.isWhitespace }) else {
            throw AccountFailure.invalidResponse
        }
    }
}
