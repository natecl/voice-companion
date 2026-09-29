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

/// Shared lavender/plum surfaces from the approved companion-room prototype.
enum ExperienceStyle {
    static let canvas = Color(red: 0.953, green: 0.949, blue: 0.961)
    static let card = Color.white
    static let accent = Color(red: 0.40, green: 0.322, blue: 0.514)
    static let ink = Color(red: 0.188, green: 0.176, blue: 0.216)
    static let surface = Color(red: 0.914, green: 0.898, blue: 0.937)
    static let secondary = Color(red: 0.48, green: 0.455, blue: 0.52)
    static let line = Color(red: 0.902, green: 0.890, blue: 0.922)
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
                .frame(width: symbolSize, height: symbolSize)
                .foregroundStyle(filled && enabled ? .white : ExperienceStyle.ink.opacity(enabled ? 1 : 0.40))
                .frame(width: size, height: size)
                .background {
                    if filled {
                        Circle().fill(enabled ? (icon == "plus" ? Color(red: 0.18, green: 0.17, blue: 0.21) : ExperienceStyle.ink) : Color(white: 0.935))
                            .overlay(Circle().strokeBorder(.white.opacity(icon == "plus" ? 0.12 : 0), lineWidth: 1))
                            .shadow(color: .black.opacity(icon == "plus" && enabled ? 0.16 : 0), radius: 12, y: 7)
                            .padding(size > 44 ? 0 : 4)
                    } else if !bare {
                        Circle().fill(.white)
                            .overlay(Circle().strokeBorder(ExperienceStyle.line, lineWidth: ["person", "magnifyingglass"].contains(icon) ? 1.5 : 0))
                            .shadow(color: ExperienceStyle.ink.opacity(0.035), radius: 12, y: 5)
                    }
                }

        }.buttonStyle(ExperiencePressStyle()).accessibilityLabel(title)
    }

    private var symbolSize: CGFloat { size > 44 ? (icon == "plus" ? 36 : 30) : 23 }

    @ViewBuilder private var buttonSymbol: some View {
        if icon == "plus" {
            Image(systemName: "plus").font(.system(size: size > 44 ? 25 : 20, weight: .bold, design: .rounded))
        } else if ["mic", "arrow.up", "xmark", "chevron.left", "stop.fill", "equal"].contains(icon) {
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
        }.buttonStyle(ExperiencePressStyle()).background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("")
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
        }.buttonStyle(ExperiencePressStyle()).background(ExperienceStyle.canvas).foregroundStyle(ExperienceStyle.ink).experienceNavigationTitle("").navigationBarBackButtonHidden(true)
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


/// Small, interruptible feedback; the hit target never shrinks with the artwork.
struct ExperiencePressStyle: ButtonStyle {
    var pressedScale: CGFloat = 0.96
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed { ExperienceHaptics.tap() }
            }
            .scaleEffect(configuration.isPressed && !reduceMotion ? pressedScale : 1)
            .opacity(configuration.isPressed ? 0.88 : 1)
            .animation(reduceMotion ? nil : (configuration.isPressed ? .easeOut(duration: 0.1) : .spring(response: 0.28, dampingFraction: 0.82)), value: configuration.isPressed)
    }
}

struct ExperienceNotice: View {
    let title: String
    let message: String
    @State private var dismissed = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        Group {
        if !dismissed {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.circle").font(.system(size: 18)).foregroundStyle(ExperienceStyle.secondary).padding(.top, 1)
            VStack(alignment: .leading, spacing: 5) {
                Text(title).font(.subheadline.weight(.semibold))
                Text(message).font(.footnote).foregroundStyle(ExperienceStyle.secondary).fixedSize(horizontal: false, vertical: true)
            }.frame(maxWidth: .infinity, alignment: .leading)
            Button {
                withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.2)) { dismissed = true }
            } label: {
                Image(systemName: "xmark").font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(ExperienceStyle.secondary).frame(width: 44, height: 44)
            }.buttonStyle(ExperiencePressStyle()).accessibilityLabel("Dismiss \(title)")
        }.padding(10).background(ExperienceStyle.surface.opacity(0.65), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(ExperienceStyle.line))
            .accessibilityElement(children: .contain)
            .transition(reduceMotion ? .identity : .opacity.combined(with: .scale(scale: 0.98, anchor: .top)))
        }
        }.onChange(of: message) { _, _ in dismissed = false }
    }
}


@MainActor
enum ExperienceHaptics {
    static func tap() {
        #if os(iOS)
        UIImpactFeedbackGenerator(style: .soft).impactOccurred(intensity: 0.55)
        #endif
    }
    static func recordingChanged() {
        #if os(iOS)
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        #endif
    }
}

/// The founder-provided chat reference uses quiet, content-sized incoming bubbles.
struct ExperienceAgentBubble: ViewModifier {
    func body(content: Content) -> some View {
        content.font(.body).lineSpacing(4)
            .padding(.horizontal, 16).padding(.vertical, 14)
            .background(ExperienceStyle.card, in: RoundedRectangle(cornerRadius: 23, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 23, style: .continuous).strokeBorder(ExperienceStyle.line.opacity(0.4), lineWidth: 0.5))
            #if os(iOS)
            .contentShape(.contextMenuPreview, RoundedRectangle(cornerRadius: 23, style: .continuous))
            #endif
    }
}
