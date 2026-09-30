#if DEBUG && os(iOS)
import SwiftUI

/// Explicit, presentation-only fixture. Never loads credentials, controllers or
/// storage, and cannot send network requests or delete any account.
struct AccountDeletionUIFixture: View {
    @State private var pending = false
    @State private var recovery = false
    private let canDelete = !ProcessInfo.processInfo.arguments.contains("--deletion-ui-disabled")

    var body: some View {
        if pending {
            ExperienceSignupView(onSignIn: { _ in }, accountMessage: recovery ? "Sign in with the same provider to finish deleting this account." : "Account deletion is pending. Retry when you’re connected.", deletingAccount: true,
                                 onRetryDeletion: recovery ? nil : { recovery = true })
        } else {
            RoomWebView(state: ["messages": [], "notes": [], "ready": true, "appearance": "light", "canSignOut": true, "canDeleteAccount": canDelete], onAction: { command in
                if command["action"] as? String == "delete-account" { pending = true }
            }, onFailure: { _ in })
            .ignoresSafeArea(.container, edges: .bottom)
        }
    }
}
#endif
