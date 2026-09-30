import GoogleSignIn
#if os(iOS)
import UIKit
#else
import AppKit
#endif

@MainActor
final class GoogleAccountProvider {
    private var signingIn = false

    #if os(iOS)
    typealias Presenter = UIViewController
    #else
    typealias Presenter = NSWindow
    #endif

    func signIn(nonce: String, presenting: Presenter, clientID: String, serverClientID: String) async throws -> ProviderAuthorization {
        guard !signingIn, !clientID.isEmpty, !serverClientID.isEmpty else { throw AccountFailure.unavailable }
        signingIn = true
        defer { signingIn = false }
        GIDSignIn.sharedInstance.configuration = GIDConfiguration(clientID: clientID, serverClientID: serverClientID)
        do {
            let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: presenting, hint: nil,
                                                                  additionalScopes: [], nonce: nonce)
            try Task.checkCancellation()
            guard let token = result.user.idToken?.tokenString, let subject = result.user.userID, !subject.isEmpty else { throw AccountFailure.invalidResponse }
            return ProviderAuthorization(identityToken: token, authorizationCode: result.serverAuthCode,
                                         providerUserID: result.user.userID, googleGrant: GoogleAccountGrant(subject: subject, token: result.user.refreshToken.tokenString))
        } catch {
            if Task.isCancelled || (error as? GIDSignInError)?.code == .canceled {
                throw AccountFailure.cancelled
            }
            throw AccountFailure.unavailable
        }
    }
}
