import AuthenticationServices

struct ProviderAuthorization: Sendable {
    let identityToken: String
    let authorizationCode: String?
    let providerUserID: String?
    var googleGrant: GoogleAccountGrant? = nil
}

@MainActor
final class AppleAccountProvider: NSObject, ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {
    private var continuation: CheckedContinuation<ProviderAuthorization, Error>?
    private var anchor: ASPresentationAnchor?
    private var controller: ASAuthorizationController?
    private var requestID: UUID?

    func signIn(nonce: String, anchor: ASPresentationAnchor) async throws -> ProviderAuthorization {
        guard continuation == nil else { throw AccountFailure.unavailable }
        let currentRequest = UUID()
        requestID = currentRequest
        self.anchor = anchor
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                self.continuation = continuation
                let request = ASAuthorizationAppleIDProvider().createRequest()
                request.nonce = nonce
                let controller = ASAuthorizationController(authorizationRequests: [request])
                self.controller = controller
                controller.delegate = self
                controller.presentationContextProvider = self
                controller.performRequests()
            }
        } onCancel: {
            Task { @MainActor in
                guard self.requestID == currentRequest else { return }
                self.controller?.cancel()
                self.finish(.failure(AccountFailure.cancelled))
            }
        }
    }

    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        // Set before performRequests, retained until the delegate finishes.
        anchor ?? ASPresentationAnchor()
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        guard controller === self.controller else { return }
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let data = credential.identityToken, let token = String(data: data, encoding: .utf8) else {
            finish(.failure(AccountFailure.invalidResponse)); return
        }
        finish(.success(ProviderAuthorization(identityToken: token,
            authorizationCode: credential.authorizationCode.flatMap { String(data: $0, encoding: .utf8) },
            providerUserID: credential.user)))
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
        guard controller === self.controller else { return }
        let cancelled = (error as? ASAuthorizationError)?.code == .canceled
        finish(.failure(cancelled ? AccountFailure.cancelled : AccountFailure.unavailable))
    }

    private func finish(_ result: Result<ProviderAuthorization, Error>) {
        let pending = continuation
        continuation = nil
        requestID = nil
        controller = nil
        anchor = nil
        pending?.resume(with: result)
    }
}
