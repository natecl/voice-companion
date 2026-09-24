import Foundation
import Security

struct RelayConfiguration: Decodable {
    let url: URL
    let token: String
    let rootCertificate: String?

    static func load() throws -> Self {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        let file: URL
        if let index = arguments.firstIndex(of: "--relay-config"), index + 1 < arguments.count {
            file = URL(fileURLWithPath: arguments[index + 1])
        } else {
            file = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("relay-client.json")
        }
        guard let data = try? Data(contentsOf: file) else { throw CaptureFailure.noRelay }
        let config = try JSONDecoder().decode(Self.self, from: data)
        let loopback = config.url.scheme == "ws" && config.url.host == "127.0.0.1"
        let encrypted = config.url.scheme == "wss" && config.rootCertificate != nil
        guard (loopback || encrypted), !config.token.isEmpty, config.url.path == "/stt" else { throw CaptureFailure.noRelay }
        return config
        #else
        throw CaptureFailure.noRelay // Distribution authentication is not configured yet.
        #endif
    }

    func makeSession() throws -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 15
        // Longer than capture + readiness/finalization deadlines; those own user-facing errors.
        configuration.timeoutIntervalForResource = Double(LiveTranscriber.recordingLimit.components.seconds) + 45
        if url.scheme == "wss" {
            guard let rootCertificate, let data = Data(base64Encoded: rootCertificate), let host = url.host,
                  SecCertificateCreateWithData(nil, data as CFData) != nil else { throw CaptureFailure.noRelay }
            return URLSession(configuration: configuration,
                              delegate: DevelopmentTrust(certificate: data, host: host), delegateQueue: nil)
        }
        return URLSession(configuration: configuration)
    }
}

/// A development-only anchor, transferred with the client config over the paired-device connection.
/// Standard expiry, chain, and hostname checks still run; no global trust settings change.
private final class DevelopmentTrust: NSObject, URLSessionDelegate {
    let certificate: Data
    let host: String
    init(certificate: Data, host: String) { self.certificate = certificate; self.host = host }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              challenge.protectionSpace.host == host,
              let trust = challenge.protectionSpace.serverTrust,
              let anchor = SecCertificateCreateWithData(nil, certificate as CFData),
              SecTrustSetPolicies(trust, SecPolicyCreateSSL(true, host as CFString)) == errSecSuccess,
              SecTrustSetAnchorCertificates(trust, [anchor] as CFArray) == errSecSuccess,
              SecTrustSetAnchorCertificatesOnly(trust, true) == errSecSuccess,
              SecTrustEvaluateWithError(trust, nil) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        completionHandler(.useCredential, URLCredential(trust: trust))
    }
}
