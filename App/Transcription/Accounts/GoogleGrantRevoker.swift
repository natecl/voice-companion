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

/// Revoke the grant captured with the backend-verified enrollment, not whichever
/// account the Google SDK happens to hold after a later failed sign-in attempt.
struct GoogleGrantRevoker: Sendable {
    private let send: @Sendable (URLRequest) async throws -> (Data, URLResponse)

    init(send: @escaping @Sendable (URLRequest) async throws -> (Data, URLResponse) = Self.send) {
        self.send = send
    }

    func revoke(_ token: String) async throws {
        guard !token.isEmpty, token.utf8.count <= 8192, !token.contains(where: { $0.isWhitespace }) else {
            throw AccountFailure.invalidResponse
        }
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-._~"))
        guard let encoded = token.addingPercentEncoding(withAllowedCharacters: allowed) else { throw AccountFailure.invalidResponse }
        var request = URLRequest(url: URL(string: "https://oauth2.googleapis.com/revoke")!)
        request.httpMethod = "POST"
        request.httpBody = Data("token=\(encoded)".utf8)
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 15
        do {
            let (data, response) = try await send(request)
            // Never infer success from a generic 400, HTML error or redirect.
            guard let http = response as? HTTPURLResponse else { throw AccountFailure.unavailable }
            if http.statusCode == 400,
               let error = try? JSONDecoder().decode(ProviderError.self, from: data), error.error == "invalid_token" {
                throw AccountFailure.providerGrantExpired
            }
            guard http.statusCode == 200 else { throw AccountFailure.unavailable }
        } catch AccountFailure.providerGrantExpired { throw AccountFailure.providerGrantExpired }
        catch {
            // Keep provider bodies, URLs and credentials out of user-visible errors.
            throw AccountFailure.unavailable
        }
    }

    private struct ProviderError: Decodable { let error: String }

    private static func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 15
        configuration.urlCache = nil
        configuration.httpCookieStorage = nil
        let session = URLSession(configuration: configuration, delegate: NoRedirect(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        return try await session.data(for: request)
    }

    private final class NoRedirect: NSObject, URLSessionTaskDelegate, Sendable {
        func urlSession(_ session: URLSession, task: URLSessionTask,
                        willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
                        completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
            completionHandler(nil)
        }
    }
}
