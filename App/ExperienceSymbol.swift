import SwiftUI

/// Small optical set based on the approved mockup: round strokes, open counters,
/// and an oval conversation mark rather than the system's rectangular bubble.
struct ExperienceSymbol: View {
    let name: String
    var body: some View {
        if ["house", "bubble.left", "person", "magnifyingglass", "doc.text", "plus"].contains(name) {
            GeometryReader { geometry in
                symbol.stroke(style: StrokeStyle(lineWidth: 1.7, lineCap: .round, lineJoin: .round))
                    .scaleEffect(x: geometry.size.width / 24, y: geometry.size.height / 24, anchor: .topLeading)
            }
        } else { Image(systemName: name).resizable().scaledToFit() }
    }
    private var symbol: Path {
        Path { p in
            switch name {
            case "house":
                p.move(to: CGPoint(x: 3, y: 10)); p.addLine(to: CGPoint(x: 12, y: 2.5)); p.addLine(to: CGPoint(x: 21, y: 10))
                p.addLine(to: CGPoint(x: 21, y: 21)); p.addQuadCurve(to: CGPoint(x: 20, y: 22), control: CGPoint(x: 21, y: 22))
                p.addLine(to: CGPoint(x: 15, y: 22)); p.addLine(to: CGPoint(x: 15, y: 15))
                p.addQuadCurve(to: CGPoint(x: 9, y: 15), control: CGPoint(x: 12, y: 12))
                p.addLine(to: CGPoint(x: 9, y: 22)); p.addLine(to: CGPoint(x: 4, y: 22))
                p.addQuadCurve(to: CGPoint(x: 3, y: 21), control: CGPoint(x: 3, y: 22)); p.closeSubpath()
            case "bubble.left":
                p.move(to: CGPoint(x: 5.5, y: 18))
                p.addCurve(to: CGPoint(x: 3, y: 10), control1: CGPoint(x: 2.5, y: 16), control2: CGPoint(x: 2, y: 12))
                p.addCurve(to: CGPoint(x: 13, y: 3), control1: CGPoint(x: 4, y: 5), control2: CGPoint(x: 8, y: 2))
                p.addCurve(to: CGPoint(x: 22, y: 11), control1: CGPoint(x: 19, y: 3), control2: CGPoint(x: 22, y: 6))
                p.addCurve(to: CGPoint(x: 9, y: 20), control1: CGPoint(x: 22, y: 18), control2: CGPoint(x: 15, y: 21))
                p.addQuadCurve(to: CGPoint(x: 3, y: 22), control: CGPoint(x: 6, y: 22))
                p.addQuadCurve(to: CGPoint(x: 5.5, y: 18), control: CGPoint(x: 5, y: 20)); p.closeSubpath()
            case "person":
                p.addEllipse(in: CGRect(x: 7, y: 2, width: 10, height: 10))
                p.move(to: CGPoint(x: 2.5, y: 22)); p.addCurve(to: CGPoint(x: 12, y: 13), control1: CGPoint(x: 2.5, y: 16), control2: CGPoint(x: 6.5, y: 13))
                p.addCurve(to: CGPoint(x: 21.5, y: 22), control1: CGPoint(x: 17.5, y: 13), control2: CGPoint(x: 21.5, y: 16))
            case "magnifyingglass":
                p.addEllipse(in: CGRect(x: 2, y: 2, width: 16, height: 16))
                p.move(to: CGPoint(x: 16, y: 16)); p.addLine(to: CGPoint(x: 22, y: 22))
            case "doc.text":
                p.move(to: CGPoint(x: 5, y: 2)); p.addLine(to: CGPoint(x: 13, y: 2)); p.addLine(to: CGPoint(x: 20, y: 9))
                p.addLine(to: CGPoint(x: 20, y: 21)); p.addQuadCurve(to: CGPoint(x: 19, y: 22), control: CGPoint(x: 20, y: 22))
                p.addLine(to: CGPoint(x: 5, y: 22)); p.addQuadCurve(to: CGPoint(x: 4, y: 21), control: CGPoint(x: 4, y: 22))
                p.addLine(to: CGPoint(x: 4, y: 3)); p.addQuadCurve(to: CGPoint(x: 5, y: 2), control: CGPoint(x: 4, y: 2))
                p.move(to: CGPoint(x: 13, y: 2)); p.addLine(to: CGPoint(x: 13, y: 9)); p.addLine(to: CGPoint(x: 20, y: 9))
                for y in [13.0, 17.0] { p.move(to: CGPoint(x: 8, y: y)); p.addLine(to: CGPoint(x: 16, y: y)) }
            default:
                p.move(to: CGPoint(x: 12, y: 3)); p.addLine(to: CGPoint(x: 12, y: 21))
                p.move(to: CGPoint(x: 3, y: 12)); p.addLine(to: CGPoint(x: 21, y: 12))
            }
        }
    }
}
