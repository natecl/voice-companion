import SwiftUI
import ThinkingOrbsKit

/// Shared neutral surfaces and typography, derived from the approved Home screen.
enum ExperienceStyle {
    static let canvas = Color.white
    static let ink = Color(white: 0.10)
    static let surface = Color(white: 0.95)
    static let line = Color(white: 0.90)
}

struct ExperienceIconButton: View {
    let title: String
    let icon: String
    var filled = false
    var size: CGFloat = 44
    let action: () -> Void
    @Environment(\.isEnabled) private var enabled

    init(_ title: String, icon: String, filled: Bool = false, size: CGFloat = 44, action: @escaping () -> Void) {
        self.title = title; self.icon = icon; self.filled = filled; self.size = size; self.action = action
    }
    var body: some View {
        Button(action: action) {
            Image(systemName: icon).font(.system(size: size > 44 ? 25 : 20, weight: .medium))
                .frame(width: size, height: size)
                .foregroundStyle(filled && enabled ? .white : ExperienceStyle.ink.opacity(enabled ? 1 : 0.35))
                .background(filled && enabled ? ExperienceStyle.ink : ExperienceStyle.surface, in: Circle())
        }.buttonStyle(.plain).accessibilityLabel(title)
    }
}

/// Reviewable UI only. Authentication is unavailable until the service is configured.
struct ExperienceSignupView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Spacer()
            Text("Create your account").font(.largeTitle.weight(.semibold))
            Text("Capture conversations. Keep what matters.").foregroundStyle(.secondary)
            VStack(spacing: 12) {
                Label("Continue with Google", systemImage: "envelope").frame(maxWidth: .infinity).padding(18)
                    .background(ExperienceStyle.surface, in: Capsule())
                Label("Continue with Apple", systemImage: "apple.logo").frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(ExperienceStyle.ink, in: Capsule())
            }.accessibilityElement(children: .combine)
            Text("Design preview · sign-in is not available in this build.").font(.caption).foregroundStyle(.secondary)
            Spacer()
        }.padding(24).background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).navigationTitle("Sign up")
    }
}

struct ExperiencePricingView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("Get more with Pro").font(.largeTitle.weight(.semibold))
                Text("More room for the conversations that matter.").foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 22) {
                    Label("Capture conversations", systemImage: "waveform")
                    Label("Return to notes and transcripts", systemImage: "doc.text")
                    Label("Talk things through with your agent", systemImage: "bubble.left")
                }.padding(24).frame(maxWidth: .infinity, alignment: .leading)
                    .background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 24))
                ForEach(["Monthly", "Annually"], id: \.self) { plan in
                    HStack { Text(plan).fontWeight(.semibold); Spacer(); Text("Price pending").foregroundStyle(.secondary) }
                        .padding(20).overlay(RoundedRectangle(cornerRadius: 20).strokeBorder(ExperienceStyle.line))
                }
                Text("Design preview · prices, plan allowances, and purchases are not configured. Features shown do not define paid-only access.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(24)
        }.background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).navigationTitle("Plans")
    }
}

/// Show motion only after a sustained wait; text communicates the state immediately.
struct ExperienceThinkingStatus: View {
    let label: String
    var active = true
    @State private var sustained = false
    @Environment(\.scenePhase) private var scenePhase
    var body: some View {
        HStack(spacing: 8) {
            if sustained {
                ThinkingOrb(state: .composing, size: .px20, theme: .light, paused: scenePhase != .active || !active)
                    .accessibilityHidden(true)
            }
            Text(label).font(.caption).foregroundStyle(.secondary)
        }.task {
            sustained = false
            do { try await Task.sleep(for: .seconds(2)); sustained = true } catch { }
        }
    }
}
