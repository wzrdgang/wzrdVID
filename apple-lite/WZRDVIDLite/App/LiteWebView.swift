import SwiftUI
import AVFoundation
import Photos
import UIKit
import WebKit

struct LiteWebView: UIViewRepresentable {
    private static let nativeExportHandlerName = "wzrdvidExport"

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
        configuration.userContentController.add(context.coordinator, name: Self.nativeExportHandlerName)

        let webView = WKWebView(frame: .zero, configuration: configuration)
        context.coordinator.attach(webView)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.scrollView.backgroundColor = .black

        loadBundledLite(in: webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    static func dismantleUIView(_ webView: WKWebView, coordinator: Coordinator) {
        webView.configuration.userContentController.removeScriptMessageHandler(forName: nativeExportHandlerName)
    }

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

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
        private struct ExportBuffer {
            var filename: String
            var mimeType: String
            var chunks: [String?]
        }

        private weak var webView: WKWebView?
        private var exportBuffers: [String: ExportBuffer] = [:]
        private var isSmokeMode: Bool {
            let environment = ProcessInfo.processInfo.environment
            let arguments = ProcessInfo.processInfo.arguments
            return environment["WZRDVID_LITE_SMOKE"] == "1" || arguments.contains("--lite-smoke")
        }

        func attach(_ webView: WKWebView) {
            self.webView = webView
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            injectNativeShellCSS(into: webView)
            injectNativeExportBridge(into: webView)
            LiteSmokeHarness.runIfNeeded(in: webView)
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == LiteWebView.nativeExportHandlerName,
                  let body = message.body as? [String: Any],
                  let action = body["action"] as? String
            else {
                return
            }

            switch action {
            case "start":
                startExport(body)
            case "chunk":
                appendExportChunk(body)
            case "finish":
                finishExport(body)
            case "error":
                print("WZRDVID_LITE_EXPORT_ERROR=\(body["message"] as? String ?? "unknown")")
            default:
                print("WZRDVID_LITE_EXPORT_ERROR=unknown action \(action)")
            }
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void
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

        private func injectNativeExportBridge(into webView: WKWebView) {
            let script = """
            (() => {
              if (window.__wzrdvidNativeExportBridgeInstalled) return;
              window.__wzrdvidNativeExportBridgeInstalled = true;
              document.addEventListener('click', async (event) => {
                const button = event.target && event.target.closest ? event.target.closest('#downloadButton') : null;
                if (!button || button.getAttribute('aria-disabled') === 'true') return;
                const exportApi = window.WZRDVID_LITE_EXPORT;
                const bridge = window.webkit?.messageHandlers?.wzrdvidExport;
                if (!bridge || !exportApi || typeof exportApi.shareRenderedClip !== 'function') return;
                event.preventDefault();
                event.stopImmediatePropagation();
                try {
                  const sent = await exportApi.shareRenderedClip();
                  if (!sent) bridge.postMessage({ action: 'error', message: 'No rendered clip is ready for native export.' });
                } catch (error) {
                  bridge.postMessage({ action: 'error', message: error?.message || String(error) });
                }
              }, true);
            })();
            """
            webView.evaluateJavaScript(script)
        }

        private func startExport(_ body: [String: Any]) {
            guard let id = body["id"] as? String else {
                print("WZRDVID_LITE_EXPORT_ERROR=start missing id")
                return
            }
            let filename = sanitizedFilename(body["filename"] as? String)
            let mimeType = (body["mimeType"] as? String) ?? "video/mp4"
            let chunkCount = max(1, min((body["chunkCount"] as? Int) ?? 0, 4096))
            exportBuffers[id] = ExportBuffer(
                filename: filename,
                mimeType: mimeType,
                chunks: Array(repeating: nil, count: chunkCount)
            )
        }

        private func appendExportChunk(_ body: [String: Any]) {
            guard let id = body["id"] as? String,
                  let index = body["index"] as? Int,
                  let data = body["data"] as? String,
                  var buffer = exportBuffers[id],
                  buffer.chunks.indices.contains(index)
            else {
                print("WZRDVID_LITE_EXPORT_ERROR=invalid export chunk")
                return
            }
            buffer.chunks[index] = data
            exportBuffers[id] = buffer
        }

        private func finishExport(_ body: [String: Any]) {
            guard let id = body["id"] as? String,
                  let buffer = exportBuffers.removeValue(forKey: id)
            else {
                print("WZRDVID_LITE_EXPORT_ERROR=finish missing buffer")
                return
            }
            guard buffer.chunks.allSatisfy({ $0 != nil }) else {
                print("WZRDVID_LITE_EXPORT_ERROR=missing export chunks")
                return
            }
            let encoded = buffer.chunks.compactMap { $0 }.joined()
            guard let data = Data(base64Encoded: encoded, options: [.ignoreUnknownCharacters]) else {
                print("WZRDVID_LITE_EXPORT_ERROR=base64 decode failed")
                return
            }

            do {
                let folder = FileManager.default.temporaryDirectory.appendingPathComponent("wzrdvid-lite-export", isDirectory: true)
                try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                let fileURL = folder.appendingPathComponent(buffer.filename)
                try data.write(to: fileURL, options: [.atomic])
                print("WZRDVID_LITE_EXPORT_READY=\(buffer.filename) \(buffer.mimeType) \(data.count)")
                validateAndSaveVideo(fileURL)
            } catch {
                print("WZRDVID_LITE_EXPORT_ERROR=\(error.localizedDescription)")
            }
        }

        private func sanitizedFilename(_ value: String?) -> String {
            let fallback = "wzrdvid-lite-export.mp4"
            guard let value, !value.isEmpty else {
                return fallback
            }
            let sanitized = value.replacingOccurrences(
                of: "[^A-Za-z0-9._-]+",
                with: "-",
                options: .regularExpression
            )
            let trimmed = sanitized.trimmingCharacters(in: CharacterSet(charactersIn: ".-"))
            if trimmed.isEmpty {
                return fallback
            }
            return String(trimmed.prefix(120))
        }

        private func validateAndSaveVideo(_ fileURL: URL) {
            Task { [weak self] in
                let asset = AVURLAsset(url: fileURL)
                let videoTracks = (try? await asset.loadTracks(withMediaType: .video)) ?? []
                let audioTracks = (try? await asset.loadTracks(withMediaType: .audio)) ?? []
                print("WZRDVID_LITE_EXPORT_MEDIA=videoTracks=\(videoTracks.count) audioTracks=\(audioTracks.count)")
                if self?.isSmokeMode == true {
                    await MainActor.run { [weak self] in
                        self?.setSmokeExportValidation(videoTracks: videoTracks.count, audioTracks: audioTracks.count)
                    }
                    return
                }
                guard !videoTracks.isEmpty else {
                    await MainActor.run { [weak self] in
                        self?.presentAlert(
                            title: "Export needs video",
                            message: "The rendered clip did not contain a Photos-compatible video track. Please render again and try Download."
                        )
                    }
                    return
                }
                self?.saveVideoToPhotoLibrary(fileURL)
            }
        }

        private func setSmokeExportValidation(videoTracks: Int, audioTracks: Int) {
            let script = "window.__wzrdvidNativeExportValidation = { videoTracks: \(videoTracks), audioTracks: \(audioTracks) };"
            webView?.evaluateJavaScript(script)
            print("WZRDVID_LITE_EXPORT_VALIDATED=videoTracks=\(videoTracks) audioTracks=\(audioTracks)")
        }

        private func saveVideoToPhotoLibrary(_ fileURL: URL) {
            PHPhotoLibrary.requestAuthorization(for: .addOnly) { [weak self] status in
                guard status == .authorized || status == .limited else {
                    print("WZRDVID_LITE_EXPORT_ERROR=photo add access denied")
                    Task { @MainActor [weak self] in
                        self?.presentAlert(
                            title: "Photo Access Needed",
                            message: "Allow WZRD.VID Lite to add videos to Photos, then tap Download again."
                        )
                    }
                    return
                }

                PHPhotoLibrary.shared().performChanges({
                    PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: fileURL)
                }) { [weak self] success, error in
                    if success {
                        print("WZRDVID_LITE_EXPORT_SAVED=\(fileURL.lastPathComponent)")
                        Task { @MainActor [weak self] in
                            self?.presentAlert(
                                title: "Saved Video",
                                message: "The rendered clip was saved to Photos."
                            )
                        }
                    } else {
                        print("WZRDVID_LITE_EXPORT_ERROR=photo save failed \(error?.localizedDescription ?? "unknown")")
                        Task { @MainActor [weak self] in
                            self?.presentAlert(
                                title: "Save Failed",
                                message: "Photos could not save this clip. Render again and try Download once more."
                            )
                        }
                    }
                }
            }
        }

        private func presentAlert(title: String, message: String) {
            DispatchQueue.main.async { [weak self] in
                guard let webView = self?.webView,
                      let presenter = Self.topViewController(from: webView.window?.rootViewController)
                else {
                    print("WZRDVID_LITE_EXPORT_ERROR=no presenter for alert")
                    return
                }

                let controller = UIAlertController(title: title, message: message, preferredStyle: .alert)
                controller.addAction(UIAlertAction(title: "OK", style: .default))
                presenter.present(controller, animated: true)
            }
        }

        private func presentShareSheet(for fileURL: URL) {
            DispatchQueue.main.async { [weak self] in
                guard let webView = self?.webView,
                      let presenter = Self.topViewController(from: webView.window?.rootViewController)
                else {
                    print("WZRDVID_LITE_EXPORT_ERROR=no presenter for share sheet")
                    return
                }

                let controller = UIActivityViewController(activityItems: [fileURL], applicationActivities: nil)
                if let popover = controller.popoverPresentationController {
                    popover.sourceView = webView
                    popover.sourceRect = CGRect(x: webView.bounds.midX, y: webView.bounds.midY, width: 0, height: 0)
                    popover.permittedArrowDirections = []
                }
                presenter.present(controller, animated: true)
            }
        }

        private static func topViewController(from root: UIViewController?) -> UIViewController? {
            if let navigation = root as? UINavigationController {
                return topViewController(from: navigation.visibleViewController)
            }
            if let tab = root as? UITabBarController {
                return topViewController(from: tab.selectedViewController)
            }
            if let presented = root?.presentedViewController {
                return topViewController(from: presented)
            }
            return root
        }
    }
}
