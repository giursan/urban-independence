import SwiftUI

/// Single-screen chat. Large type and high contrast for older users.
struct ChatView: View {
    @State private var model = ChatViewModel()
    @State private var recognizer = SpeechRecognizer()
    @State private var input = ""
    @FocusState private var inputFocused: Bool

    private let greeting = "Hello! I'm your companion. How are you feeling today?"

    private var isListening: Bool { recognizer.state == .listening }

    var body: some View {
        VStack(spacing: 0) {
            messageList
            composer
        }
        .background(Color(.systemGroupedBackground))
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    model.speakReplies.toggle()
                    if !model.speakReplies { model.speaker.stop() }
                } label: {
                    Image(systemName: model.speakReplies ? "speaker.wave.2.fill" : "speaker.slash.fill")
                }
                .accessibilityLabel(model.speakReplies ? "Mute spoken replies" : "Speak replies aloud")
            }
        }
        .onChange(of: recognizer.transcript) { _, newValue in
            if isListening { input = newValue }
        }
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    if model.messages.isEmpty {
                        Text(greeting)
                            .font(.title3)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: .infinity)
                            .padding(.top, 60)
                    }

                    ForEach(model.messages) { message in
                        bubble(for: message).id(message.id)
                    }

                    if model.isStreaming, model.messages.last?.text.isEmpty == true {
                        Text("Thinking…")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if let errorText = model.errorText {
                        Text(errorText)
                            .font(.body)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    Color.clear.frame(height: 1).id("bottom")
                }
                .padding(16)
            }
            .onChange(of: model.messages.last?.text) { _, _ in
                withAnimation(.easeOut(duration: 0.15)) { proxy.scrollTo("bottom", anchor: .bottom) }
            }
        }
    }

    private func bubble(for message: ChatMessage) -> some View {
        let isUser = message.role == .user
        return HStack {
            if isUser { Spacer(minLength: 40) }
            Text(message.text)
                .font(.title3)
                .foregroundStyle(isUser ? Color.white : Color.primary)
                .padding(.horizontal, 18)
                .padding(.vertical, 12)
                .background(isUser ? Color.accentColor : Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            if !isUser { Spacer(minLength: 40) }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 10) {
            Button(action: toggleMic) {
                Image(systemName: isListening ? "mic.fill" : "mic")
                    .font(.system(size: 30))
                    .foregroundStyle(isListening ? Color.red : Color.accentColor)
                    .symbolEffect(.pulse, isActive: isListening)
            }
            .disabled(model.isStreaming)
            .accessibilityLabel(isListening ? "Stop talking and send" : "Talk")

            TextField(isListening ? "Listening…" : "Type your message…", text: $input, axis: .vertical)
                .font(.title3)
                .lineLimit(1...4)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                .focused($inputFocused)
                .disabled(isListening)
                .onSubmit(send)

            Button(action: send) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 40))
            }
            .disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || model.isStreaming || isListening)
        }
        .padding(12)
        .background(.bar)
    }

    private func send() {
        let text = input
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        input = ""
        model.send(text)
    }

    /// Tap to start dictating; tap again to stop and send what was heard.
    private func toggleMic() {
        if isListening {
            let text = recognizer.stop()
            input = ""
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { model.send(trimmed) }
            return
        }

        model.speaker.stop()
        inputFocused = false
        Task {
            guard await recognizer.requestAuthorization() else { return }
            input = ""
            try? recognizer.start()
        }
    }
}

#Preview {
    ChatView()
}
