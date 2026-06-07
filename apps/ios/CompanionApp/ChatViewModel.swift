import Foundation
import Observation

/// Holds the conversation state and drives streaming turns.
@MainActor
@Observable
final class ChatViewModel {
    private(set) var messages: [ChatMessage] = []
    private(set) var isStreaming = false
    var errorText: String?

    /// When true, completed replies are read aloud.
    var speakReplies = true

    let speaker = SpeechSynthesizer()

    /// Stable per-session id; the backend upserts a conversation row for it.
    private let conversationID = UUID().uuidString
    private let service = ChatService()

    /// Sends the user's text and streams the assistant reply in place.
    func send(_ rawText: String) {
        let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }

        speaker.stop()
        errorText = nil
        messages.append(ChatMessage(role: .user, text: text))

        // Placeholder assistant bubble we fill as deltas arrive.
        let reply = ChatMessage(role: .assistant, text: "")
        messages.append(reply)
        let replyID = reply.id
        isStreaming = true

        // The backend loads incoming messages as history, so send everything
        // except the empty placeholder we just appended.
        let history = Array(messages.dropLast())

        Task {
            defer { isStreaming = false }
            do {
                for try await delta in service.stream(messages: history, conversationID: conversationID) {
                    if let idx = messages.firstIndex(where: { $0.id == replyID }) {
                        messages[idx].text += delta
                    }
                }
                // If the stream produced nothing, drop the empty bubble.
                if let idx = messages.firstIndex(where: { $0.id == replyID }) {
                    if messages[idx].text.isEmpty {
                        messages.remove(at: idx)
                        errorText = "No reply received. Is the backend running on \(AppConfig.apiBaseURL.absoluteString)?"
                    } else if speakReplies {
                        speaker.speak(messages[idx].text)
                    }
                }
            } catch {
                if let idx = messages.firstIndex(where: { $0.id == replyID }), messages[idx].text.isEmpty {
                    messages.remove(at: idx)
                }
                errorText = error.localizedDescription
            }
        }
    }
}
