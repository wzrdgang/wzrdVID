import SwiftUI
import WebKit

struct LiteWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []

        let webpagePreferences = WKWebpagePreferences()
        webpagePreferences.allowsContentJavaScript = true
        configuration.defaultWebpagePreferences = webpagePreferences

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.scrollView.backgroundColor = .black

        loadBundledLite(in: webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    private func loadBundledLite(in webView: WKWebView) {
        guard
            let liteRoot = Bundle.main.url(forResource: "LiteWeb", withExtension: nil),
            let indexURL = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "LiteWeb/lite")
        else {
            webView.loadHTMLString(Self.missingBundleHTML, baseURL: nil)
            return
        }

        webView.loadFileURL(indexURL, allowingReadAccessTo: liteRoot)
    }

    private static let missingBundleHTML = """
    <!doctype html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="font-family:-apple-system;background:#050505;color:#fff;padding:24px">
      <h1>WZRD.VID Lite bundle missing</h1>
      <p>Run <code>python3 apple-lite/scripts/prepare_lite_web_bundle.py</code> and add the generated LiteWeb folder to the app target.</p>
    </body>
    </html>
    """

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            injectNativeShellCSS(into: webView)
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.cancel)
                return
            }

            decisionHandler(Self.isAllowedLocalURL(url) ? .allow : .cancel)
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            nil
        }

        private static func isAllowedLocalURL(_ url: URL) -> Bool {
            switch url.scheme?.lowercased() {
            case "file", "about", "blob", "data":
                return true
            default:
                return false
            }
        }

        private func injectNativeShellCSS(into webView: WKWebView) {
            let script = """
            (() => {
              if (document.getElementById('wzrdvid-native-lite-style')) return;
              document.documentElement.classList.add('wzrdvid-native-lite');
              const style = document.createElement('style');
              style.id = 'wzrdvid-native-lite-style';
              style.textContent = '.wzrdvid-native-lite .back-link { display: none !important; }';
              document.head.appendChild(style);
            })();
            """
            webView.evaluateJavaScript(script)
        }
    }
}
