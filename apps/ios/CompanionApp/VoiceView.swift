import SwiftUI

/// Full-screen, voice-only companion for elderly users. Tap to begin, then just
/// talk — the orb listens, the companion replies aloud, and listening resumes
/// automatically. No typing.
struct VoiceView: View {
    @State private var model = VoiceConversationViewModel()

    private var statusText: String {
        switch model.state {
        case .idle:      return "Tap to talk with your companion"
        case .listening: return "I'm listening…"
        case .thinking:  return "Thinking…"
        case .speaking:  return "Speaking…"
        case .denied:    return "Microphone access is needed"
        }
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color(red: 0.06, green: 0.07, blue: 0.12), Color(red: 0.10, green: 0.12, blue: 0.20)],
                startPoint: .top, endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 28) {
                Spacer()

                Text(statusText)
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.white)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                VoiceOrbView(state: model.state, level: model.level)
                    .frame(height: 340)
                    .onTapGesture { toggle() }

                // Live caption — helps users who are hard of hearing follow along.
                Text(model.caption)
                    .font(.title3)
                    .foregroundStyle(.white.opacity(0.85))
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity, minHeight: 90, alignment: .top)
                    .padding(.horizontal, 28)

                Spacer()

                if model.state == .denied {
                    Text("Please allow Microphone and Speech Recognition in Settings, then reopen the app.")
                        .font(.body)
                        .foregroundStyle(.white.opacity(0.7))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                }

                controlButton
                    .padding(.bottom, 28)
            }
        }
        .statusBarHidden(true)
        .task { await model.start() }
        .onDisappear { model.end() }
    }

    @ViewBuilder
    private var controlButton: some View {
        switch model.state {
        case .idle, .denied:
            Button(action: toggle) {
                Label("Start talking", systemImage: "mic.fill")
                    .font(.title3.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(Color.accentColor, in: Capsule())
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 40)
        default:
            Button(action: { model.end() }) {
                Label("End", systemImage: "xmark")
                    .font(.title3.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(Color.red.opacity(0.85), in: Capsule())
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 40)
        }
    }

    private func toggle() {
        switch model.state {
        case .idle, .denied:
            Task { await model.start() }
        default:
            model.end()
        }
    }
}

#Preview {
    VoiceView()
}
