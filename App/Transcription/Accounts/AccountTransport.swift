import Foundation

enum AccountProvider: String, Codable, Sendable { case google, apple }

enum AccountFailure: Error, LocalizedError, Sendable {
    case unavailable, invalidResponse, signInRequired, cancelled, deletionPending, noDeletionPending, providerGrantExpired
    var errorDescription: String? {
        switch self {
        case .unavailable: "Sign-in is unavailable right now. Please try again."
        case .invalidResponse: "The account service returned an invalid response. Please try again."
        case .signInRequired: "Please sign in again to continue."
        case .cancelled: "Sign-in was cancelled."
        case .deletionPending: "Account deletion is pending. Sign in again to finish deleting it."
        case .providerGrantExpired: "Sign in with the same Google account to finish removing its authorization."
        case .noDeletionPending: "There is no pending deletion for this sign-in."
        }
    }
}

struct AccountChallenge: Decodable, Sendable {
    let challenge: String
    let nonce: String
    let expires: Double
}

struct AccountSession: Codable, Sendable {
    let token: String
    let refreshToken: String
    let owner: String
    let expires: Double
    let refreshExpires: Double
    enum CodingKeys: String, CodingKey {
        case token, owner, expires
        case refreshToken = "refresh_token", refreshExpires = "refresh_expires"
    }

    func validate(now: Date = .now) throws {
        guard UUID(uuidString: owner) != nil,
              (32...256).contains(token.utf8.count), (32...256).contains(refreshToken.utf8.count),
              !token.contains(where: { $0.isWhitespace }), !refreshToken.contains(where: { $0.isWhitespace }),
              expires.isFinite, refreshExpires.isFinite,
              expires > now.timeIntervalSince1970, refreshExpires > now.timeIntervalSince1970 else {
            throw AccountFailure.invalidResponse
        }
    }
}

struct AccountTransport: Sendable {
    let endpoint: URL

    init(endpoint: URL) throws {
        guard endpoint.scheme == "wss", endpoint.host?.isEmpty == false,
              endpoint.path == "/account", endpoint.user == nil, endpoint.password == nil,
              endpoint.query == nil, endpoint.fragment == nil else { throw AccountFailure.unavailable }
        self.endpoint = endpoint
    }

    func challenge(for provider: AccountProvider) async throws -> AccountChallenge {
        let data = try await request(operation: "challenge", fields: ["provider": provider.rawValue])
        let result = try JSONDecoder().decode(AccountChallenge.self, from: data)
        guard (32...256).contains(result.challenge.utf8.count), result.nonce.count == 64,
              result.nonce.allSatisfy({ $0.isHexDigit }), result.expires.isFinite,
              result.expires > Date.now.timeIntervalSince1970 else { throw AccountFailure.invalidResponse }
        return result
    }

    func exchange(provider: AccountProvider, challenge: String, identityToken: String, authorizationCode: String? = nil) async throws -> AccountSession {
        var fields = ["provider": provider.rawValue, "challenge": challenge, "identity_token": identityToken]
        if provider == .apple {
            guard let authorizationCode, !authorizationCode.isEmpty else { throw AccountFailure.invalidResponse }
            fields["authorization_code"] = authorizationCode
        }
        return try await session(operation: "exchange", fields: fields)
    }

    func refresh(_ token: String) async throws -> AccountSession {
        try await session(operation: "refresh", fields: ["refresh_token": token])
    }

    func signOut(_ token: String) async throws {
        _ = try await request(operation: "sign_out", fields: ["refresh_token": token])
    }

    func deleteAccount(_ refreshToken: String) async throws {
        try await deletionResult(operation: "delete_account", fields: ["refresh_token": refreshToken, "confirmation": "delete_account"])
    }

    func resumeDeletion(_ deletionToken: String) async throws {
        try await deletionResult(operation: "resume_deletion", fields: ["deletion_token": deletionToken])
    }

    func recoverDeletion(provider: AccountProvider, challenge: String, identityToken: String, authorizationCode: String? = nil, expectedOwner: String? = nil) async throws -> AccountDeletionReceipt {
        var fields = ["provider": provider.rawValue, "challenge": challenge, "identity_token": identityToken, "confirmation": "delete_account"]
        if provider == .apple {
            guard let authorizationCode, !authorizationCode.isEmpty else { throw AccountFailure.invalidResponse }
            fields["authorization_code"] = authorizationCode
        }
        if let expectedOwner { fields["expected_owner"] = expectedOwner }
        let data = try await request(operation: "recover_deletion", fields: fields)
        let receipt = try JSONDecoder().decode(AccountDeletionReceipt.self, from: data)
        guard receipt.status == "pending" else { throw AccountFailure.invalidResponse }
        try PendingAccountDeletion(endpoint: endpoint, provider: provider, receipt: receipt).validate()
        return receipt
    }

    private func deletionResult(operation: String, fields: [String: String]) async throws {
        let data = try await request(operation: operation, fields: fields)
        struct Result: Decodable { let status: String }
        guard try JSONDecoder().decode(Result.self, from: data).status == "deleted" else { throw AccountFailure.invalidResponse }
    }

    private func session(operation: String, fields: [String: String]) async throws -> AccountSession {
        let data = try await request(operation: operation, fields: fields)
        let session = try JSONDecoder().decode(AccountSession.self, from: data)
        try session.validate()
        return session
    }

    private func request(operation: String, fields: [String: String]) async throws -> Data {
        var payload: [String: Any] = fields
        payload["version"] = 1
        payload["operation"] = operation
        let data = try JSONSerialization.data(withJSONObject: payload)
        guard data.count <= 20_000 else { throw AccountFailure.invalidResponse }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 15
        let session = URLSession(configuration: configuration)
        let socket = session.webSocketTask(with: endpoint)
        socket.maximumMessageSize = 20_000
        defer { socket.cancel(with: .goingAway, reason: nil); session.invalidateAndCancel() }
        return try await withTaskCancellationHandler {
            socket.resume()
            // Explicit deadline also bounds a server that upgrades then stays silent.
            return try await withThrowingTaskGroup(of: Data.self) { group in
                group.addTask {
                    try await socket.send(.string(String(decoding: data, as: UTF8.self)))
                    let message = try await socket.receive()
                    let response: Data
                    switch message {
                    case .string(let value): response = Data(value.utf8)
                    case .data(let value): response = value
                    @unknown default: throw AccountFailure.invalidResponse
                    }
                    return response
                }
                group.addTask {
                    try await Task.sleep(for: .seconds(15))
                    socket.cancel(with: .goingAway, reason: nil)
                    throw AccountFailure.unavailable
                }
                defer { group.cancelAll() }
                guard let response = try await group.next() else { throw AccountFailure.unavailable }
                let envelope = try JSONDecoder().decode(AccountEnvelope.self, from: response)
                if envelope.type == "error" {
                    if ["unauthorized", "refresh_replayed"].contains(envelope.message) { throw AccountFailure.signInRequired }
                    if envelope.message == "account_deletion_pending" { throw AccountFailure.deletionPending }
                    if envelope.message == "no_account_deletion_pending" { throw AccountFailure.noDeletionPending }
                    throw AccountFailure.unavailable
                }
                guard envelope.type == "account_result", envelope.version == 1,
                      envelope.operation == operation else { throw AccountFailure.invalidResponse }
                return response
            }
        } onCancel: { socket.cancel(with: .goingAway, reason: nil) }
    }
}

private struct AccountEnvelope: Decodable {
    let type: String
    let version: Int?
    let operation: String?
    let message: String?
}
