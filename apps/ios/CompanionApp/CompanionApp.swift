import SwiftUI

@main
struct CompanionApp: App {
    var body: some Scene {
        WindowGroup {
            // Voice-first experience for elderly users — no typing.
            VoiceView()
                .preferredColorScheme(.dark)
        }
    }
}
