import Foundation
import Observation

/// Drives a hands-free voice conversation: listen → (pause detected) → send →
/// stream reply → speak it → listen again, looping until the user ends it.
@MainActor
@Observable
final class VoiceConversationViewModel {
    enum State: Equatable {
        case idle
        case listening
        case thinking
        case speaking
        case denied
    }

    private(set) var state: State = .idle
    /// Live text to show under the orb (the user's words, then the reply).
    private(set) var caption = ""
    /// 0...1 microphone loudness, for the orb animation while listening.
    private(set) var level: Double = 0

    private let recognizer = SpeechRecognizer()
    private let synthesizer = SpeechSynthesizer()
    private let service = ChatService()
    private let conversationID = UUID().uuidString

    private var messages: [ChatMessage] = []
    private var silenceTask: Task<Void, Never>?
    private var active = false

    /// How long a pause in speech ends the user's turn.
    private let endOfTurnPause: Duration = .seconds(1.6)

    init() {
        recognizer.onResult = { [weak self] text in self?.handlePartial(text) }
        recognizer.onLevel = { [weak self] level in self?.level = level }
        synthesizer.onFinish = { [weak self] in self?.handleSpeechFinished() }
    }

    /// Requests permission and begins the listening loop.
    func start() async {
        guard state != .listening, state != .thinking, state != .speaking else { return }
        guard await recognizer.requestAuthorization() else {
            state = .denied
            return
        }
        active = true
        beginListening()
    }

    /// Ends the conversation and releases the microphone.
    func end() {
        active = false
        silenceTask?.cancel()
        recognizer.stop()
        synthesizer.stop()
        level = 0
        caption = ""
        state = .idle
    }

    // MARK: - Loop

    private func beginListening() {
        guard active else { return }
        caption = ""
        state = .listening
        do {
            try recognizer.start()
        } catch {
            state = .idle
        }
    }

    private func handlePartial(_ text: String) {
        guard state == .listening else { return }
        caption = text
        scheduleEndOfTurn()
    }

    /// Restart the pause timer on every partial result; firing it ends the turn.
    private func scheduleEndOfTurn() {
        silenceTask?.cancel()
        silenceTask = Task { [weak self] in
            guard let pause = self?.endOfTurnPause else { return }
            try? await Task.sleep(for: pause)
            guard !Task.isCancelled else { return }
            self?.finalizeTurn()
        }
    }

    private func finalizeTurn() {
        guard active, state == .listening else { return }
        let text = recognizer.stop().trimmingCharacters(in: .whitespacesAndNewlines)
        level = 0
        if text.isEmpty {
            beginListening()  // heard only noise; keep waiting
        } else {
            sendTurn(text)
        }
    }

    private func sendTurn(_ text: String) {
        messages.append(ChatMessage(role: .user, text: text))
        caption = text
        state = .thinking

        let reply = ChatMessage(role: .assistant, text: "")
        messages.append(reply)
        let replyID = reply.id
        let history = Array(messages.dropLast())

        Task {
            do {
                var accumulated = ""
                for try await delta in service.stream(messages: history, conversationID: conversationID) {
                    accumulated += delta
                    caption = accumulated
                    if let idx = messages.firstIndex(where: { $0.id == replyID }) {
                        messages[idx].text = accumulated
                    }
                }
                let final = accumulated.trimmingCharacters(in: .whitespacesAndNewlines)
                if final.isEmpty {
                    messages.removeAll { $0.id == replyID }
                    beginListening()
                } else {
                    speak(final)
                }
            } catch {
                messages.removeAll { $0.id == replyID }
                speak("Sorry, I had trouble connecting. Let's try again.")
            }
        }
    }

    private func speak(_ text: String) {
        guard active else { return }
        state = .speaking
        caption = text
        synthesizer.speak(text)
    }

    private func handleSpeechFinished() {
        guard active else { return }
        beginListening()
    }
}
