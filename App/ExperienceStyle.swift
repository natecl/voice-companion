import SwiftUI
import ThinkingOrbsKit
#if os(iOS)
import UIKit
#else
import AppKit
#endif

enum ExperienceClipboard {
    static func copy(_ text: String) {
        #if os(iOS)
        UIPasteboard.general.string = text
        #else
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        #endif
    }
}

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
                            .shadow(color: .black.opacity(0.06), radius: 16, y: 7)
                    }
                }

        }.buttonStyle(.plain).accessibilityLabel(title)
    }

    @ViewBuilder private var buttonSymbol: some View {
        if ["mic", "arrow.up", "xmark", "chevron.left", "stop.fill"].contains(icon) {
            Image(systemName: icon)
                .font(.system(size: icon == "stop.fill" ? 17 : icon == "mic" ? 18 : 20, weight: icon == "mic" ? .regular : .semibold))
        } else {
            ExperienceSymbol(name: icon)
        }
    }
}

/// Reviewable UI only. Authentication is unavailable until the service is configured.
struct ExperienceSignupView: View {
    @State private var notice = false
    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                VStack(spacing: 0) {
                    Color.clear.frame(height: max(40, geometry.size.height * 0.16))
                    Text("Ellis").font(.title2.bold()).padding(.bottom, 40)
                    Text("Create your account").font(.system(.title, weight: .bold)).multilineTextAlignment(.center)
                    Text("Capture conversations. Keep what matters.").font(.callout).foregroundStyle(ExperienceStyle.secondary).multilineTextAlignment(.center).padding(.top, 10)
                    VStack(spacing: 12) {
                        Button { notice = true } label: {
                            HStack(spacing: 14) {
                                Text("G").font(.system(size: 27, weight: .bold)).foregroundStyle(AngularGradient(colors: [.blue, .green, .yellow, .red, .blue], center: .center))
                                Text("Continue with Google").font(.body.weight(.medium))
                            }.frame(maxWidth: .infinity).frame(height: 50).experienceCard(radius: 25)
                        }
                        Button { notice = true } label: {
                            Label("Continue with Apple", systemImage: "apple.logo").font(.body.weight(.medium))
                                .frame(maxWidth: .infinity).frame(height: 50).foregroundStyle(.white).background(ExperienceStyle.ink, in: Capsule())
                        }
                    }.padding(.top, 44)
                    Button { notice = true } label: {
                        (Text("Already have an account? ").foregroundStyle(ExperienceStyle.secondary) + Text("Log in").foregroundStyle(ExperienceStyle.ink)).font(.footnote)
                    }.padding(.top, 36)
                    Spacer(minLength: 70)
                    Text("Design preview · sign-in is not connected.").font(.caption2).foregroundStyle(ExperienceStyle.secondary)
                    Button("Terms and Privacy Policy") { notice = true }.font(.caption).padding(.top, 12).padding(.bottom, 28)
                }.padding(.horizontal, 22).frame(minHeight: geometry.size.height)
            }
        }.background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("")
            .alert("Account preview", isPresented: $notice) { Button("OK", role: .cancel) {} } message: { Text("Sign-in and legal links are not configured in this internal build.") }
    }
}

struct ExperiencePricingView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedPlan = "Monthly"
    @State private var notice = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HStack { Spacer(); ExperienceIconButton("Close plans", icon: "xmark") { dismiss() } }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Get more with Pro").font(.system(size: 32, weight: .bold))
                    Text("More room for your conversations.").font(.body).foregroundStyle(ExperienceStyle.secondary)
                }.padding(.top, 12)
                VStack(alignment: .leading, spacing: 22) {
                    feature("More recording time", icon: "mic")
                    feature("More conversations with your agent", icon: "bubble.left")
                    feature("Live transcripts", icon: "text.alignleft")
                    feature("Notes and summaries", icon: "doc.text")
                    feature("Find details from past conversations", icon: "magnifyingglass")
                    Divider()
                    Text("Core features are also available on Free.").font(.caption).foregroundStyle(ExperienceStyle.secondary).frame(maxWidth: .infinity)
                }.padding(18).experienceCard(radius: 16)
                ForEach(["Monthly", "Annually"], id: \.self) { plan in
                    Button { selectedPlan = plan } label: {
                        HStack(spacing: 14) {
                            Image(systemName: selectedPlan == plan ? "largecircle.fill.circle" : "circle").font(.system(size: 21)).foregroundStyle(selectedPlan == plan ? ExperienceStyle.ink : ExperienceStyle.secondary)
                            Text(plan).font(.body.weight(.semibold)); Spacer()
                            Text(plan == "Monthly" ? "$— / month" : "$— / year").font(.body)
                        }.padding(16).background(selectedPlan == plan ? ExperienceStyle.surface.opacity(0.6) : .white, in: RoundedRectangle(cornerRadius: 14))
                            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(selectedPlan == plan ? ExperienceStyle.ink : ExperienceStyle.line))
                    }.accessibilityAddTraits(selectedPlan == plan ? .isSelected : [])
                }
                Text("Pricing and limits to be confirmed.").font(.caption).foregroundStyle(ExperienceStyle.secondary).frame(maxWidth: .infinity)
                Button { notice = true } label: { Text("Continue with Pro").font(.body.weight(.semibold)).frame(maxWidth: .infinity).frame(height: 48).foregroundStyle(.white).background(ExperienceStyle.ink, in: RoundedRectangle(cornerRadius: 13)) }
                Button("Continue free") { dismiss() }.font(.body.weight(.semibold)).frame(maxWidth: .infinity).frame(minHeight: 44)
                Button("Terms   ·   Privacy   ·   Restore") { notice = true }.font(.caption).foregroundStyle(ExperienceStyle.secondary).frame(maxWidth: .infinity)
            }.padding(20)
        }.background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("").navigationBarBackButtonHidden(true)
            .alert("Plan preview", isPresented: $notice) { Button("OK", role: .cancel) {} } message: { Text("Purchases, plan limits, legal links and restoration are not configured in this internal build.") }
    }
    private func feature(_ title: String, icon: String) -> some View {
        HStack(spacing: 20) { ExperienceSymbol(name: icon).frame(width: 22, height: 22); Text(title).font(.callout) }
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

struct ExperienceCard: ViewModifier {
    var radius: CGFloat
    var elevated: Bool
    func body(content: Content) -> some View {
        content.background(.white, in: RoundedRectangle(cornerRadius: radius))
            .overlay(RoundedRectangle(cornerRadius: radius).strokeBorder(ExperienceStyle.line, lineWidth: 0.8))
            .shadow(color: .black.opacity(elevated ? 0.065 : 0), radius: 18, y: 8)
    }
}
extension View {
    func experienceCard(radius: CGFloat = 22, elevated: Bool = false) -> some View { modifier(ExperienceCard(radius: radius, elevated: elevated)) }
}
