import SwiftUI

/// Account styling follows Home; unavailable services remain explicit previews.
struct ExperienceAccountView: View {
    @Binding var useMemory: Bool
    let recordingLimit: Int64
    let onDone: () -> Void
    @State private var previewNotice = false
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    HStack {
                        ExperienceIconButton("Done", icon: "chevron.left", action: onDone)
                        Spacer(); Text("Account").font(.headline); Spacer()
                        Color.clear.frame(width: 44, height: 44)
                    }.padding(.bottom, 8)
                    HStack(spacing: 20) {
                        ExperienceSymbol(name: "person").frame(width: 25, height: 28).frame(width: 58, height: 58).experienceCard(radius: 29)
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Your account").font(.headline)
                            Text("Internal development build").font(.footnote).foregroundStyle(ExperienceStyle.secondary)
                        }; Spacer()
                    }.padding(.vertical, 8)
                    group("Plan") {
                        NavigationLink { ExperiencePricingView() } label: { row("Plan preview", detail: "Manage plan") }.accessibilityLabel("Plan preview")
                    }
                    group("Preferences") {
                        NavigationLink { detail("Microphone & speech access", text: "Microphone and speech permissions are requested when you start capture or dictation. You can change these permissions in system Settings. Capture starts only when you tap +. This build limits recordings to \(recordingLimit) seconds.") } label: { row("Microphone & speech access") }
                        Divider()
                        NavigationLink {
                            VStack(alignment: .leading, spacing: 24) {
                                Toggle("Use past memory", isOn: $useMemory)
                                Text("Dictated questions stay in your conversation and are kept out of meeting notes. Deleting a recording may retain learned memories; the deletion confirmation explains what is removed.").foregroundStyle(ExperienceStyle.secondary)
                                Spacer()
                            }.padding(24).experienceNavigationTitle("Privacy & data")
                        } label: { row("Privacy & data") }
                    }
                    group("Support") {
                        NavigationLink { detail("Help & feedback", text: "This is an internal preview. Share feedback with the team through your existing testing channel.") } label: { row("Help & feedback") }
                        Divider()
                        Button { previewNotice = true } label: { row("Terms of service") }
                        Divider()
                        Button { previewNotice = true } label: { row("Privacy policy") }
                    }
                    NavigationLink { ExperienceSignupView() } label: { row("Sign-up preview").padding(.horizontal, 14).experienceCard(radius: 14) }
                    Text("Sign-in, sign-out, account deletion and subscriptions are not connected in this build.").font(.caption).foregroundStyle(ExperienceStyle.secondary).padding(.horizontal, 12)
                }.padding(.horizontal, 20).padding(.bottom, 24)
            }.buttonStyle(ExperiencePressStyle()).background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).tint(ExperienceStyle.ink)
                .navigationTitle("")
                .alert("Not configured", isPresented: $previewNotice) { Button("OK", role: .cancel) {} } message: { Text("Legal links are not yet configured for this internal build.") }
        }.frame(minWidth: 320, minHeight: 480)
    }
    private func group<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title).font(.footnote.weight(.medium)).foregroundStyle(ExperienceStyle.secondary).padding(.vertical, 14)
            Divider(); content()
        }.padding(.horizontal, 14).experienceCard(radius: 15)
    }
    private func row(_ title: String, detail: String? = nil) -> some View {
        HStack {
            Text(title).font(.callout); Spacer()
            if let detail { Text(detail).font(.footnote).foregroundStyle(ExperienceStyle.secondary) }
            Image(systemName: "chevron.right").font(.footnote).foregroundStyle(ExperienceStyle.secondary)
        }.frame(minHeight: 48).contentShape(Rectangle())
    }
    private func detail(_ title: String, text: String) -> some View {
        VStack(alignment: .leading) { Text(text).foregroundStyle(ExperienceStyle.secondary); Spacer() }.padding(24).experienceNavigationTitle(title)
    }
}
