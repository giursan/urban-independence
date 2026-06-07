import AVFoundation
import Foundation
import Observation
import Speech

/// On-device speech-to-text using Apple's Speech framework. Streams a live
/// partial transcript and a microphone audio level (for the orb animation)
/// via callbacks; `stop()` returns the final text.
///
/// Note: dictation works best on a physical device. On the Simulator it relies
/// on the Mac's microphone (enable I/O → Audio Input in the Simulator menu).
@MainActor
@Observable
final class SpeechRecognizer {
    enum State: Equatable {
        case idle
        case listening
        case unavailable
    }

    private(set) var state: State = .idle
    private(set) var transcript = ""

    /// Called on the main actor with the latest partial transcript.
    var onResult: ((String) -> Void)?
    /// Called on the main actor with a 0...1 microphone loudness for animation.
    var onLevel: ((Double) -> Void)?

    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    /// Requests microphone + speech-recognition permission. Returns true if both granted.
    func requestAuthorization() async -> Bool {
        let speechOK = await withCheckedContinuation { (cont: CheckedContinuation<Bool, Never>) in
            SFSpeechRecognizer.requestAuthorization { status in
                cont.resume(returning: status == .authorized)
            }
        }
        let micOK = await withCheckedContinuation { (cont: CheckedContinuation<Bool, Never>) in
            AVAudioApplication.requestRecordPermission { granted in
                cont.resume(returning: granted)
            }
        }
        return speechOK && micOK
    }

    func start() throws {
        guard let recognizer, recognizer.isAvailable else {
            state = .unavailable
            return
        }

        task?.cancel()
        task = nil
        transcript = ""

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
        try session.setActive(true, options: .notifyOthersOnDeactivation)

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        self.request = request

        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            request.append(buffer)
            let level = Self.loudness(buffer)
            Task { @MainActor in self?.onLevel?(level) }
        }

        audioEngine.prepare()
        try audioEngine.start()
        state = .listening

        task = recognizer.recognitionTask(with: request) { [weak self] result, error in
            let text = result?.bestTranscription.formattedString
            let finished = error != nil || (result?.isFinal ?? false)
            Task { @MainActor in
                guard let self else { return }
                if let text {
                    self.transcript = text
                    self.onResult?(text)
                }
                if finished, self.state == .listening { _ = self.stop() }
            }
        }
    }

    /// Stops listening and returns the accumulated transcript.
    @discardableResult
    func stop() -> String {
        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        state = .idle
        onLevel?(0)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        return transcript
    }

    /// Root-mean-square loudness of a buffer, scaled to a lively 0...1 range.
    private static func loudness(_ buffer: AVAudioPCMBuffer) -> Double {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let count = Int(buffer.frameLength)
        guard count > 0 else { return 0 }
        var sum: Float = 0
        for i in 0..<count {
            let sample = channel[i]
            sum += sample * sample
        }
        let rms = sqrtf(sum / Float(count))
        return min(1.0, Double(rms) * 12.0)
    }
}
