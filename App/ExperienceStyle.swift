import SwiftUI
import ThinkingOrbsKit

/// Shared neutral surfaces and typography, derived from the approved Home screen.
enum ExperienceStyle {
    static let canvas = Color.white
    static let ink = Color(red: 0.035, green: 0.045, blue: 0.055)
    static let surface = Color(white: 0.945)
    static let secondary = Color(red: 0.46, green: 0.47, blue: 0.52)
    static let line = Color(white: 0.925)
}

struct ExperienceIconButton: View {
    let title: String
    let icon: String
    var filled = false
    var bare = false
    var size: CGFloat = 44
    let action: () -> Void
    @Environment(\.isEnabled) private var enabled

    init(_ title: String, icon: String, filled: Bool = false, bare: Bool = false, size: CGFloat = 44, action: @escaping () -> Void) {
        self.title = title; self.icon = icon; self.filled = filled; self.bare = bare; self.size = size; self.action = action
    }
    var body: some View {
        Button(action: action) {
            buttonSymbol
                .frame(width: size > 44 ? 30 : 23, height: size > 44 ? 30 : 23)
                .foregroundStyle(filled && enabled ? .white : ExperienceStyle.ink.opacity(enabled ? 1 : 0.40))
                .frame(width: size, height: size)
                .background {
                    if filled {
                        Circle().fill(enabled ? ExperienceStyle.ink : Color(white: 0.935))
                            .padding(size > 44 ? 0 : 4)
                    } else if !bare {
                        Circle().fill(.white)
                            .shadow(color: .black.opacity(0.035), radius: 14, y: 5)
                    }
                }

        }.buttonStyle(.plain).accessibilityLabel(title)
    }

    @ViewBuilder private var buttonSymbol: some View {
        if icon == "mic" || icon == "arrow.up" {
            Image(systemName: icon)
                .font(.system(size: icon == "mic" ? 18 : 20, weight: icon == "mic" ? .regular : .semibold))
        } else {
            ExperienceSymbol(name: icon)
        }
    }
}

/// Reviewable UI only. Authentication is unavailable until the service is configured.
struct ExperienceSignupView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Spacer()
            Text("Create your account").font(.title.weight(.semibold))
            Text("Capture conversations. Keep what matters.").foregroundStyle(ExperienceStyle.secondary)
            VStack(spacing: 12) {
                HStack(spacing: 12) { Text("G").font(.headline); Text("Continue with Google") }.frame(maxWidth: .infinity).padding(18)
                    .background(.white, in: Capsule()).overlay(Capsule().strokeBorder(ExperienceStyle.line))
                Label("Continue with Apple", systemImage: "apple.logo").frame(maxWidth: .infinity).padding(18)
                    .foregroundStyle(.white).background(ExperienceStyle.ink, in: Capsule())
            }.accessibilityElement(children: .combine)
            Text("Design preview · sign-in is not available in this build.").font(.caption).foregroundStyle(ExperienceStyle.secondary)
            Spacer()
        }.padding(24).background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("")
    }
}

struct ExperiencePricingView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("Get more with Pro").font(.title.weight(.semibold))
                Text("More room for the conversations that matter.").foregroundStyle(ExperienceStyle.secondary)
                VStack(alignment: .leading, spacing: 22) {
                    Label("Capture conversations", systemImage: "waveform")
                    HStack(spacing: 12) { ExperienceSymbol(name: "doc.text").frame(width: 22, height: 22); Text("Return to notes and transcripts") }
                    HStack(spacing: 12) { ExperienceSymbol(name: "bubble.left").frame(width: 22, height: 22); Text("Talk things through with your agent") }
                }.padding(24).frame(maxWidth: .infinity, alignment: .leading)
                    .background(ExperienceStyle.surface, in: RoundedRectangle(cornerRadius: 24))
                ForEach(["Monthly", "Annually"], id: \.self) { plan in
                    HStack { Text(plan).fontWeight(.semibold); Spacer(); Text("Price pending").foregroundStyle(ExperienceStyle.secondary) }
                        .padding(20).overlay(RoundedRectangle(cornerRadius: 20).strokeBorder(ExperienceStyle.line))
                }
                Text("Design preview · prices, plan allowances, and purchases are not configured. Features shown do not define paid-only access.")
                    .font(.caption).foregroundStyle(ExperienceStyle.secondary)
            }.padding(24)
        }.background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("")
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
            Text(label).font(.caption).foregroundStyle(ExperienceStyle.secondary)
        }.task {
            sustained = false
            do { try await Task.sleep(for: .seconds(2)); sustained = true } catch { }
        }
    }
}

extension View {
    @ViewBuilder func experienceNavigationTitle(_ title: String) -> some View {
        #if os(iOS)
        navigationTitle(title).navigationBarTitleDisplayMode(.inline)
        #else
        navigationTitle(title)
        #endif
    }
}
