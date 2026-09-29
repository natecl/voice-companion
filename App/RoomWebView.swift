#if os(iOS)
import SwiftUI
import WebKit

/// The browser preview and phone load the same local files. Audio and credentials never enter JS.
struct RoomWebView: UIViewRepresentable {
    let state: [String: Any]
    let onAction: ([String: Any]) -> Void
    let onFailure: (String) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onAction: onAction, onFailure: onFailure) }
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.userContentController.add(context.coordinator, name: "room")
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = context.coordinator
        web.isOpaque = false; web.backgroundColor = .clear
        web.scrollView.isScrollEnabled = false
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.allowsLinkPreview = false
        #if DEBUG
        web.isInspectable = true
        #endif
        context.coordinator.web = web
        context.coordinator.state = state
        guard let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "RoomUI") else {
            onFailure("The interface could not be loaded. Please reopen the app."); return web
        }
        context.coordinator.entry = url
        web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        return web
    }
    func updateUIView(_ web: WKWebView, context: Context) {
        context.coordinator.state = state
        context.coordinator.sendState()
    }
    static func dismantleUIView(_ web: WKWebView, coordinator: Coordinator) {
        web.configuration.userContentController.removeScriptMessageHandler(forName: "room")
        web.navigationDelegate = nil
    }
    @MainActor final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        weak var web: WKWebView?
        var entry: URL?
        var state: [String: Any] = [:]
        var ready = false
        private var lastData: Data?
        private var delivering = false
        let onAction: ([String: Any]) -> Void
        let onFailure: (String) -> Void
        init(onAction: @escaping ([String: Any]) -> Void, onFailure: @escaping (String) -> Void) {
            self.onAction = onAction; self.onFailure = onFailure
        }
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "room", message.frameInfo.isMainFrame,
                  message.frameInfo.request.url?.standardizedFileURL == entry?.standardizedFileURL,
                  let value = message.body as? [String: Any], value["version"] as? Int == 1,
                  let action = value["action"] as? String else { return }
            if action == "ready" { ready = true; lastData = nil; sendState() }
            else { onAction(value) }
        }
        func sendState() {
            guard ready, !delivering, let web,
                  let data = try? JSONSerialization.data(withJSONObject: state, options: [.sortedKeys]), data != lastData else { return }
            delivering = true; lastData = data
            // Arguments are serialized by WebKit, never interpolated into executable source.
            web.callAsyncJavaScript("window.room.render(state);", arguments: ["state": state], in: nil, in: .page) { [weak self] result in
                guard let self else { return }; self.delivering = false
                switch result {
                case .success: self.sendState()
                case .failure: self.ready = false; self.onFailure("The interface stopped responding. Please reopen the app. Your saved conversations are safe.")
                }
            }
        }
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            decisionHandler(action.targetFrame?.isMainFrame == true && action.request.url?.standardizedFileURL == entry?.standardizedFileURL ? .allow : .cancel)
        }
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            ready = false; lastData = nil; webView.reload()
        }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            onFailure("The interface could not be loaded. Please reopen the app.")
        }
    }
}
#endif
