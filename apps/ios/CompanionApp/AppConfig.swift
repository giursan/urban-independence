import Foundation

/// Central configuration. Point `apiBaseURL` at your running FastAPI backend.
///
/// On the iOS Simulator, `localhost` reaches the Mac host, so the default works
/// when you run `uvicorn app.main:app --reload` inside `apps/api`. On a physical
/// device, change this to your Mac's LAN IP (e.g. http://192.168.1.20:8000) and
/// add that host to NSAppTransportSecurity, since NSAllowsLocalNetworking only
/// covers loopback/.local.
enum AppConfig {
    static let apiBaseURL = URL(string: "https://apricot-chlorine-motion.ngrok-free.dev")!
    static let demoToken = ""

    /// Conversation mode the backend tags new conversations with.
    static let mode = "companion"
}
