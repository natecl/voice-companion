import SwiftUI
import GoogleSignIn
import Observation

private struct AccountSignOutKey: EnvironmentKey {
    static let defaultValue: (@MainActor @Sendable () -> Void)? = nil
}
extension EnvironmentValues {
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
    var message: String?
    private var generation = UUID()
    private var manager: AccountSessionManager?
    private let apple = AppleAccountProvider()
    private let google = GoogleAccountProvider()

    func restore() async {
        guard !ready else { return }
        defer { ready = true }
        do {
            let account = try AccountCredentialStore.load()
            manager = AccountSessionManager(account: account)
            if account != nil { active = try await manager?.current() }
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
            let config = try AccountConfiguration()
            let challenge = try await config.transport.challenge(for: provider)
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
            case .apple: authorization = try await apple.signIn(nonce: challenge.nonce, anchor: window)
            case .google: authorization = try await google.signIn(nonce: challenge.nonce, presenting: presenter,
                clientID: config.googleClientID, serverClientID: config.googleServerClientID)
            }
            let session = try await config.transport.exchange(provider: provider, challenge: challenge.challenge,
                                                              identityToken: authorization.identityToken)
            let account = StoredAccount(endpoint: config.transport.endpoint, provider: provider, session: session)
            if manager == nil { manager = AccountSessionManager(account: nil) }
            try await manager?.install(account)
            generation = UUID()
            legacy = false
            active = account
        } catch AccountFailure.cancelled { message = nil }
        catch { message = error.localizedDescription }
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

    var body: some View {
        Group {
            if !runtime.ready { ProgressView().tint(ExperienceStyle.accent) }
            else if runtime.legacy || runtime.active != nil {
                content(runtime.active != nil)
                    .id(runtime.active?.session.owner ?? "legacy")
                    .environment(\.accountSignOut, signOutAction)
            } else {
                ExperienceSignupView(onSignIn: { provider in Task { await runtime.signIn(provider) } },
                                     isBusy: runtime.busy, accountMessage: runtime.message)
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
