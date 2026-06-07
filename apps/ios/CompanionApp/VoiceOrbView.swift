import SwiftUI

/// A glowing, animated orb that reacts to the conversation state: it swells with
/// the user's voice while listening, and breathes gently while thinking/speaking.
struct VoiceOrbView: View {
    let state: VoiceConversationViewModel.State
    let level: Double

    @State private var breathe = false
    @State private var rotate = false

    private var colors: [Color] {
        switch state {
        case .listening: return [Color(red: 0.40, green: 0.80, blue: 1.0), Color(red: 0.20, green: 0.45, blue: 0.95)]
        case .thinking:  return [Color(red: 0.70, green: 0.55, blue: 1.0), Color(red: 0.45, green: 0.30, blue: 0.95)]
        case .speaking:  return [Color(red: 0.45, green: 0.95, blue: 0.70), Color(red: 0.20, green: 0.70, blue: 0.55)]
        case .denied:    return [Color(white: 0.6), Color(white: 0.35)]
        case .idle:      return [Color(red: 0.55, green: 0.75, blue: 1.0), Color(red: 0.35, green: 0.50, blue: 0.90)]
        }
    }

    private var scale: CGFloat {
        switch state {
        case .listening: return 1.0 + CGFloat(level) * 0.7
        case .thinking, .speaking: return breathe ? 1.10 : 0.92
        default: return 1.0
        }
    }

    var body: some View {
        ZStack {
            // Soft outer halo
            Circle()
                .fill(RadialGradient(colors: colors + [.clear], center: .center, startRadius: 10, endRadius: 200))
                .frame(width: 320, height: 320)
                .blur(radius: 40)
                .opacity(0.55)

            // Rotating gradient core
            Circle()
                .fill(AngularGradient(colors: colors + colors.reversed(), center: .center))
                .frame(width: 220, height: 220)
                .blur(radius: 14)
                .rotationEffect(.degrees(rotate ? 360 : 0))

            // Bright center
            Circle()
                .fill(RadialGradient(colors: [.white.opacity(0.9)] + colors, center: .center, startRadius: 2, endRadius: 120))
                .frame(width: 200, height: 200)
                .blur(radius: 2)
        }
        .scaleEffect(scale)
        .animation(.easeOut(duration: 0.18), value: level)
        .animation(.easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: breathe)
        .onAppear {
            breathe = true
            withAnimation(.linear(duration: 14).repeatForever(autoreverses: false)) { rotate = true }
        }
    }
}
