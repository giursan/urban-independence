import SwiftUI

@main
struct CompanionApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ChatView()
                    .navigationTitle("Companion")
                    .navigationBarTitleDisplayMode(.inline)
            }
        }
    }
}
