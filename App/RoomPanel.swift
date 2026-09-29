import SwiftUI

/// The prototype's single edge-to-edge panel, shared by every accessory flow.
/// Content determines height, capped at 88% so longer notes remain scrollable.
struct RoomPanel<Content: View>: View {
    let title: String
    let closeLabel: String
    let onClose: () -> Void
    @ViewBuilder let content: Content
    @State private var contentHeight: CGFloat = 300
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .bottom) {
                Color(red: 20/255, green: 16/255, blue: 29/255).opacity(0.22)
                    .ignoresSafeArea().onTapGesture(perform: onClose).accessibilityHidden(true)
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Capsule().fill(ExperienceStyle.line).frame(width: 34, height: 4)
                            .frame(maxWidth: .infinity).padding(.top, 10).padding(.bottom, 14)
                            .accessibilityHidden(true)
                        HStack(spacing: 12) {
                            Text(title).font(.system(size: 17, weight: .medium)).fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                            ExperienceIconButton(closeLabel, icon: "xmark", size: 38, action: onClose)
                        }.padding(.bottom, 24)
                        content
                    }.padding(.horizontal, 20).padding(.bottom, max(34, geometry.safeAreaInsets.bottom))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { contentHeight = $0 }
                }.scrollIndicators(.hidden)
                    .frame(height: min(contentHeight, geometry.size.height * 0.88))
                    .background(ExperienceStyle.canvas)
                    .clipShape(UnevenRoundedRectangle(topLeadingRadius: 32, topTrailingRadius: 32))
                    .shadow(color: .black.opacity(0.08), radius: 30, y: -10)
                    .transition(reduceMotion ? .opacity : .move(edge: .bottom).combined(with: .opacity))
                    .accessibilityAddTraits(.isModal)
            }
        }.ignoresSafeArea(edges: .bottom)
            .font(RoomTypography.body(15)).tracking(-0.25).foregroundStyle(ExperienceStyle.ink)
            .tint(ExperienceStyle.accent).buttonStyle(ExperiencePressStyle())
            #if os(macOS)
            .onExitCommand(perform: onClose)
            #endif
    }
}

struct RoomToast: View {
    let message: String
    let onDismiss: () -> Void
    var body: some View {
        HStack(spacing: 8) {
            Text(message).font(RoomTypography.body(13)).fixedSize(horizontal: false, vertical: true)
            Button(action: onDismiss) { RoomIcon(name: "close").frame(width: 16, height: 16).frame(width: 28, height: 28) }
                .accessibilityLabel("Dismiss message")
        }.padding(.vertical, 10).padding(.leading, 18).padding(.trailing, 10)
            .foregroundStyle(ExperienceStyle.canvas).background(ExperienceStyle.ink, in: RoundedRectangle(cornerRadius: 24))
            .shadow(color: .black.opacity(0.08), radius: 20, y: 5)
            .accessibilityElement(children: .contain).accessibilityIdentifier("roomToast")
    }
}

struct RoomTitle: ViewModifier {
    func body(content: Content) -> some View { content.font(.custom("Georgia", size: 29)).tracking(-1).lineSpacing(3.25).fixedSize(horizontal: false, vertical: true).padding(.top, 4) }
}
struct RoomRow: ViewModifier {
    func body(content: Content) -> some View { content.font(RoomTypography.body(15)).padding(.vertical, 14).frame(minHeight: 54).contentShape(Rectangle()).overlay(alignment: .bottom) { Rectangle().fill(ExperienceStyle.line).frame(height: 1) } }
}
struct RoomPrimaryButton: ViewModifier {
    func body(content: Content) -> some View { content.font(.system(size: 16, weight: .medium)).foregroundStyle(ExperienceStyle.onAccent).frame(maxWidth: .infinity).padding(.vertical, 14).background(ExperienceStyle.accent, in: RoundedRectangle(cornerRadius: 24)) }
}

/// A circular 36-point send control centered in the 38 × 44 composer slot.
/// Its hit area stays full size while the mic and arrow crossfade.
struct RoomComposerButton: View {
    let title: String
    let icon: String
    var filled = false
    let action: () -> Void
    @Environment(\.isEnabled) private var enabled
    init(_ title: String, icon: String, filled: Bool = false, action: @escaping () -> Void) {
        self.title = title; self.icon = icon; self.filled = filled; self.action = action
    }
    var body: some View {
        Button(action: action) {
            Image(RoomIcon.assets[icon] ?? "Room-arrow-up").resizable().scaledToFit()
                .frame(width: 23, height: 23)
                .frame(width: 36, height: 36)
                .foregroundStyle(filled ? ExperienceStyle.onAccent : ExperienceStyle.ink)
                .background { if filled { Circle().fill(ExperienceStyle.accent) } }
                .frame(width: 38, height: 44)
                .opacity(enabled ? 1 : 0.4)
                .contentShape(Rectangle())
        }.buttonStyle(ExperiencePressStyle()).accessibilityLabel(title)
    }
}
