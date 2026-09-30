import SwiftUI
import GoogleSignIn
import Observation

private struct AccountSignOutKey: EnvironmentKey {
    static let defaultValue: (@MainActor @Sendable () -> Void)? = nil
}
private struct AccountDeleteKey: EnvironmentKey {
    static let defaultValue: (@MainActor @Sendable () -> Void)? = nil
}
extension EnvironmentValues {
    var accountDelete: (@MainActor @Sendable () -> Void)? {
        get { self[AccountDeleteKey.self] }
        set { self[AccountDeleteKey.self] = newValue }
    }
    var accountSignOut: (@MainActor @Sendable () -> Void)? {
        get { self[AccountSignOutKey.self] }
        set { self[AccountSignOutKey.self] = newValue }
    }
}
extension Notification.Name {
    static let accountWillChange = Notification.Name("ai.voicecompanion.accountWillChange")
}

@MainActor @Observable
final class AccountRuntime {
    var ready = false
    var legacy = false
    var active: StoredAccount?
    var busy = false
    var pendingDeletion: PendingAccountDeletion?
    var recoveringDeletion = false
    private let deletionController = AccountDeletionController()
    var message: String?
    private var generation = UUID()
    private var manager: AccountSessionManager?
    private let apple = AppleAccountProvider()
    private let google = GoogleAccountProvider()

    func restore() async {
        guard !ready else { return }
        defer { ready = true }
        do {
            manager = AccountSessionManager.shared
            if let pending = try AccountCredentialStore.pendingDeletion() {
                pendingDeletion = pending
                message = pending.serverDeleted ? "Your account was deleted. Finish removing its data from this device." : "Account deletion is pending. Retry when you’re connected."
                return
            }
            let account = try AccountCredentialStore.load()
            manager = AccountSessionManager.shared
            if let account {
                try await manager?.install(account, restoring: true)
                active = try await manager?.current()
            }
            else if try !AccountCredentialStore.hasEnrollmentState() {
                legacy = try RelayCredentialStore.load() != nil
            }
        } catch { message = error.localizedDescription }
    }

    func signIn(_ provider: AccountProvider) async {
        guard !busy else { return }
        busy = true; message = nil
        defer { busy = false }
        do {
            if let pending = pendingDeletion, provider != pending.provider { throw AccountFailure.noDeletionPending }
            let config = try AccountConfiguration()
            let revocationOnly = recoveringDeletion && pendingDeletion?.serverDeleted == true
            let challenge = revocationOnly ? nil : try await config.transport.challenge(for: provider)
            let nonce = challenge?.nonce ?? UUID().uuidString
            let authorization: ProviderAuthorization
            #if os(iOS)
            guard let window = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene })
                .flatMap(\.windows).first(where: \.isKeyWindow),
                  let presenter = window.rootViewController else { throw AccountFailure.unavailable }
            #else
            guard let window = NSApplication.shared.keyWindow else { throw AccountFailure.unavailable }
            let presenter = window
            #endif
            switch provider {
            case .apple: authorization = try await apple.signIn(nonce: nonce, anchor: window)
            case .google: authorization = try await google.signIn(nonce: nonce, presenting: presenter,
                clientID: config.googleClientID, serverClientID: config.googleServerClientID)
            }
            if recoveringDeletion {
                if let original = pendingDeletion, original.serverDeleted {
                    guard provider == .google, let fresh = authorization.googleGrant else { throw AccountFailure.noDeletionPending }
                    // Server erasure is already complete. Revoke only the same
                    // previously verified Google identity; do not enroll again.
                    let pending = try original.replacingGoogleGrant(fresh)
                    try AccountCredentialStore.saveDeletion(pending)
                    pendingDeletion = pending
                    try await finishDeletion(pending)
                    return
                }
                guard let challenge else { throw AccountFailure.invalidResponse }
                let receipt = try await config.transport.recoverDeletion(provider: provider, challenge: challenge.challenge,
                    identityToken: authorization.identityToken, authorizationCode: authorization.authorizationCode, expectedOwner: pendingDeletion?.owner)
                let pending = PendingAccountDeletion(endpoint: config.transport.endpoint, provider: provider, receipt: receipt, googleGrant: authorization.googleGrant)
                if let previous = pendingDeletion, previous.owner != pending.owner { throw AccountFailure.invalidResponse }
                try AccountCredentialStore.saveDeletion(pending)
                pendingDeletion = pending
                try await finishDeletion(pending)
                return
            }
            guard let challenge else { throw AccountFailure.invalidResponse }
            let session = try await config.transport.exchange(provider: provider, challenge: challenge.challenge,
                                                              identityToken: authorization.identityToken, authorizationCode: authorization.authorizationCode)
            let account = StoredAccount(endpoint: config.transport.endpoint, provider: provider, session: session, googleGrant: authorization.googleGrant)
            if manager == nil { manager = AccountSessionManager.shared }
            try await manager?.install(account)
            generation = UUID()
            legacy = false
            active = account
        } catch AccountFailure.providerGrantExpired {
            recoveringDeletion = true
            message = AccountFailure.providerGrantExpired.localizedDescription
        } catch AccountFailure.deletionPending {
            recoveringDeletion = true
            message = "Sign in with the same provider to finish the account deletion you requested."
        } catch AccountFailure.cancelled { message = nil }
        catch { message = error.localizedDescription }
    }

    func deleteAccount() async {
        guard active != nil, !busy, AccountConfiguration.deletionEnabled else { return }
        busy = true; message = nil; generation = UUID()
        defer { busy = false }
        do {
            let pending = try await AccountSessionManager.shared.prepareDeletion()
            pendingDeletion = pending
            NotificationCenter.default.post(name: .accountWillChange, object: nil)
            active = nil; legacy = false
            try await finishDeletion(pending)
        } catch AccountFailure.signInRequired {
            recoveringDeletion = pendingDeletion != nil
            message = "Sign in with the same provider to finish deleting this account."
        } catch AccountFailure.providerGrantExpired {
            recoveringDeletion = true
            message = AccountFailure.providerGrantExpired.localizedDescription
        } catch { message = "Account deletion could not finish. Your request is saved if it was started. Please retry." }
    }

    func retryDeletion() async {
        guard let pending = pendingDeletion, !busy else { return }
        busy = true; message = nil
        defer { busy = false }
        do { try await finishDeletion(pending) }
        catch AccountFailure.signInRequired {
            recoveringDeletion = true
            message = "Sign in with the same provider to finish deleting this account."
        }
        catch AccountFailure.providerGrantExpired {
            recoveringDeletion = true
            message = AccountFailure.providerGrantExpired.localizedDescription
        }
        catch { message = "Deletion could not finish. Check your connection and retry. Your account will stay closed here." }
    }

    private func finishDeletion(_ pending: PendingAccountDeletion) async throws {
        do { try await deletionController.finish(pending) }
        catch {
            // The controller may have durably completed server erasure before
            // a local/revocation failure. Recovery must use that saved phase.
            if let saved = try? AccountCredentialStore.pendingDeletion(), saved.id == pending.id {
                pendingDeletion = saved
            }
            throw error
        }
        guard pendingDeletion?.id == pending.id else { throw AccountFailure.cancelled }
        pendingDeletion = nil; recoveringDeletion = false
        active = nil; legacy = false
        GIDSignIn.sharedInstance.signOut()
        message = "Your account was deleted."
    }

    func refreshCurrent() async {
        guard active != nil, !busy else { return }
        let expected = generation
        do {
            let refreshed = try await manager?.current()
            guard generation == expected else { return }
            active = refreshed
        }
        catch {
            guard generation == expected else { return }
            NotificationCenter.default.post(name: .accountWillChange, object: nil)
            active = nil
            message = "Please sign in again to continue."
        }
    }

    func maintain() async {
        while !Task.isCancelled, active != nil {
            await refreshCurrent()
            do { try await Task.sleep(for: .seconds(30)) }
            catch { return }
        }
    }

    func signOut() async {
        guard let previous = active, !busy else { return }
        busy = true
        generation = UUID()
        defer { busy = false }
        do {
            // Revoke first; an offline failure remains visible and can be retried.
            try await AccountTransport(endpoint: previous.endpoint).signOut(previous.session.refreshToken)
            NotificationCenter.default.post(name: .accountWillChange, object: nil)
            active = nil
            _ = try await manager?.removeLocalAccount()
            try RecordingNotesCache.shared.clear(owner: previous.session.owner)
            GIDSignIn.sharedInstance.signOut()
            active = nil
            message = nil
        } catch { message = "Sign-out could not finish. Check your connection and try again." }
    }
}

struct AccountRootView<Content: View>: View {
    @State private var runtime = AccountRuntime()
    @Environment(\.scenePhase) private var scenePhase
    @ViewBuilder var content: (Bool) -> Content

    private var signOutAction: (@MainActor @Sendable () -> Void)? {
        guard runtime.active != nil else { return nil }
        return { Task { await runtime.signOut() } }
    }

    private var deleteAction: (@MainActor @Sendable () -> Void)? {
        guard runtime.active != nil, AccountConfiguration.deletionEnabled else { return nil }
        return { Task { await runtime.deleteAccount() } }
    }

    private var retryDeletionAction: (() -> Void)? {
        guard runtime.pendingDeletion != nil, !runtime.recoveringDeletion else { return nil }
        return { Task { await runtime.retryDeletion() } }
    }

    private var leaveRecoveryAction: (() -> Void)? {
        guard runtime.recoveringDeletion, runtime.pendingDeletion == nil else { return nil }
        return { runtime.recoveringDeletion = false; runtime.message = nil }
    }

    var body: some View {
        Group {
            if !runtime.ready { ProgressView().tint(ExperienceStyle.accent) }
            else if runtime.legacy || runtime.active != nil {
                content(runtime.active != nil)
                    .id(runtime.active?.session.owner ?? "legacy")
                    .environment(\.accountSignOut, signOutAction)
                    .environment(\.accountDelete, deleteAction)
            } else {
                ExperienceSignupView(onSignIn: { provider in Task { await runtime.signIn(provider) } },
                                     isBusy: runtime.busy, accountMessage: runtime.message,
                                     deletingAccount: runtime.pendingDeletion != nil || runtime.recoveringDeletion,
                                     onRetryDeletion: retryDeletionAction,
                                     onLeaveRecovery: leaveRecoveryAction)
            }
        }
        .task { await runtime.restore() }
        .task(id: runtime.active?.session.owner) { await runtime.maintain() }
        .onOpenURL { _ = GIDSignIn.sharedInstance.handle($0) }
        .alert("Account", isPresented: Binding(get: { runtime.active != nil && runtime.message != nil }, set: { if !$0 { runtime.message = nil } })) {
            Button("OK", role: .cancel) { runtime.message = nil }
        } message: { Text(runtime.message ?? "") }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active, runtime.active != nil { Task { await runtime.refreshCurrent() } }
        }
    }
}
