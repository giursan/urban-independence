import SwiftUI

@main
struct AporiaApp: App {
    var body: some Scene {
        WindowGroup {
            // Voice-first experience for elderly users — no typing.
            VoiceView()
                .preferredColorScheme(.dark)
        }
    }
}
