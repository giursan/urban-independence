import Foundation

/// Talks to the FastAPI `/chat` endpoint, which speaks the Vercel AI SDK v6
/// data-stream protocol (Server-Sent Events). We POST the running message list
/// plus a stable `conversation_id`, then decode the SSE stream into text deltas.
///
/// The wire format is a sequence of `data: {json}` lines. Assistant text arrives
/// as `{"type":"text-delta","delta":"..."}` events; the stream ends with a
/// `finish` event and a final `data: [DONE]`. We tolerate unknown event types.
struct ChatService {

    enum ChatError: LocalizedError {
        case badStatus(Int)
        case server(String)

        var errorDescription: String? {
            switch self {
            case .badStatus(let code): return "Server returned status \(code)."
            case .server(let msg): return msg
            }
        }
    }

    // MARK: Request encoding

    private struct OutgoingPart: Encodable {
        let type = "text"
        let text: String
    }

    private struct OutgoingMessage: Encodable {
        let id: String
        let role: String
        let parts: [OutgoingPart]
    }

    private struct RequestBody: Encodable {
        let id: String
        let messages: [OutgoingMessage]
        let conversation_id: String
        let trigger = "submit-message"
    }

    // MARK: SSE event decoding

    private struct StreamEvent: Decodable {
        let type: String
        let delta: String?
        let text: String?
        let errorText: String?
    }

    /// Streams assistant text deltas for the given message history.
    func stream(messages: [ChatMessage], conversationID: String) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let body = RequestBody(
                        id: conversationID,
                        messages: messages.map {
                            OutgoingMessage(
                                id: $0.id,
                                role: $0.role.rawValue,
                                parts: [OutgoingPart(text: $0.text)]
                            )
                        },
                        conversation_id: conversationID
                    )

                    var request = URLRequest(url: AppConfig.apiBaseURL.appendingPathComponent("chat"))
                    request.httpMethod = "POST"
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    request.setValue("true", forHTTPHeaderField: "ngrok-skip-browser-warning")
                    if !AppConfig.demoToken.isEmpty {
                        request.setValue(AppConfig.demoToken, forHTTPHeaderField: "X-Aporia-Demo-Token")
                    }
                    request.httpBody = try JSONEncoder().encode(body)

                    let (bytes, response) = try await URLSession.shared.bytes(for: request)

                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        throw ChatError.badStatus(http.statusCode)
                    }

                    let decoder = JSONDecoder()
                    for try await line in bytes.lines {
                        guard line.hasPrefix("data:") else { continue }
                        let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                        if payload.isEmpty { continue }
                        if payload == "[DONE]" { break }

                        guard let data = payload.data(using: .utf8),
                              let event = try? decoder.decode(StreamEvent.self, from: data)
                        else { continue }

                        switch event.type {
                        case "text-delta":
                            if let d = event.delta { continuation.yield(d) }
                        case "text":
                            if let t = event.text { continuation.yield(t) }
                        case "error":
                            throw ChatError.server(event.errorText ?? "Aporia ran into an error.")
                        default:
                            continue
                        }
                    }
                    continuation.finish()
                } catch is CancellationError {
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}
