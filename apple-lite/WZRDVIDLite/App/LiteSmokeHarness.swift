#if DEBUG
import Darwin
import Foundation
import WebKit

enum LiteSmokeHarness {
    static func runIfNeeded(in webView: WKWebView) {
        let environment = ProcessInfo.processInfo.environment
        let arguments = ProcessInfo.processInfo.arguments
        guard environment["WZRDVID_LITE_SMOKE"] == "1" || arguments.contains("--lite-smoke") else {
            return
        }

        Task { @MainActor in
            do {
                let value = try await webView.callAsyncJavaScript(smokeScript, arguments: [:], in: nil, contentWorld: .page)
                finish(with: value as Any)
            } catch {
                print("WZRDVID_LITE_SMOKE_ERROR=\(error.localizedDescription)")
                fflush(stdout)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                    Darwin.exit(2)
                }
            }
        }
    }

    private static func finish(with result: Any) {
        let passed: Bool
        if let result = result as? [String: Any],
           JSONSerialization.isValidJSONObject(result),
           let data = try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]),
           let json = String(data: data, encoding: .utf8) {
            passed = (result["passed"] as? Bool) == true
            print("WZRDVID_LITE_SMOKE_RESULT=\(json)")
        } else {
            passed = false
            print("WZRDVID_LITE_SMOKE_ERROR=Unexpected smoke result")
        }

        fflush(stdout)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            Darwin.exit(passed ? 0 : 2)
        }
    }

    private static let smokeScript = """
      const result = {
        passed: false,
        checks: {},
        capabilities: {},
        warnings: [],
        errors: []
      };
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const check = (name, value, detail = '') => {
        result.checks[name] = Boolean(value);
        if (!value) result.errors.push(detail ? `${name}: ${detail}` : name);
      };
      const text = (selector) => (document.querySelector(selector)?.textContent || '').trim();
      try {
        await sleep(350);

        const mediaInput = document.querySelector('#mediaInput');
        const languageSelect = document.querySelector('[data-i18n-language-select]');
        const durationSelect = document.querySelector('#durationSelect');
        const randomClip = document.querySelector('#randomClipAssembly');
        const renderButton = document.querySelector('#renderButton');
        const downloadButton = document.querySelector('#downloadButton');
        const fileList = document.querySelector('#fileList');
        const canvas = document.querySelector('#previewCanvas');

        check('liteLoaded', Boolean(mediaInput && languageSelect && durationSelect && randomClip && renderButton && downloadButton && canvas));
        check('fileInputSurface', Boolean(mediaInput && mediaInput.type === 'file' && mediaInput.accept.includes('video') && mediaInput.accept.includes('image')));

        result.capabilities.fileConstructor = typeof File === 'function';
        result.capabilities.dataTransfer = typeof DataTransfer === 'function';
        result.capabilities.blob = typeof Blob === 'function';
        result.capabilities.objectURL = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function';
        result.capabilities.mediaRecorder = typeof MediaRecorder === 'function';
        result.capabilities.captureStream = typeof canvas?.captureStream === 'function';
        result.capabilities.navigatorShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
        check('exportBlobSurface', Boolean(result.capabilities.blob && result.capabilities.objectURL && downloadButton && 'download' in downloadButton));

        localStorage.setItem('wzrdvid.uiLanguage', 'es');
        window.WZRD_I18N?.apply(document);
        await sleep(150);
        check('languageSpanish', document.documentElement.lang === 'es' && /Idioma|Borrador|archivos/i.test(document.body.textContent || ''), document.documentElement.lang);

        durationSelect.value = '15';
        durationSelect.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(75);
        check('duration15', durationSelect.value === '15' && /15/.test(renderButton.textContent || ''), renderButton.textContent || '');

        randomClip.checked = true;
        randomClip.dispatchEvent(new Event('change', { bubbles: true }));
        check('randomCheckbox', randomClip.checked === true);

        if (result.capabilities.fileConstructor && result.capabilities.dataTransfer) {
          const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=';
          const bytes = Uint8Array.from(atob(pngBase64), (char) => char.charCodeAt(0));
          const file = new File([bytes], 'lite-smoke.png', { type: 'image/png' });
          const transfer = new DataTransfer();
          transfer.items.add(file);
          mediaInput.files = transfer.files;
          mediaInput.dispatchEvent(new Event('change', { bubbles: true }));
          for (let index = 0; index < 80; index += 1) {
            if ((fileList.textContent || '').includes('lite-smoke.png')) break;
            await sleep(100);
          }
          check('localFileImportSynthetic', (fileList.textContent || '').includes('lite-smoke.png'), text('#fileList'));
        } else {
          check('localFileImportSynthetic', false, 'File/DataTransfer unavailable in WKWebView smoke context');
        }

        if (result.checks.localFileImportSynthetic && result.capabilities.mediaRecorder && result.capabilities.captureStream) {
          renderButton.click();
          for (let index = 0; index < 360; index += 1) {
            if ((downloadButton.getAttribute('href') || '').startsWith('blob:')) break;
            await sleep(100);
          }
          check('randomRenderCompleted', (downloadButton.getAttribute('href') || '').startsWith('blob:'), text('#statusLine'));
          check('exportDownloadReady', Boolean(downloadButton.download && downloadButton.download.includes('wzrdvid-lite-15s')), downloadButton.download || '');
        } else {
          check('randomRenderCompleted', false, 'MediaRecorder/canvas capture unavailable or local import failed');
          check('exportDownloadReady', false, 'Render did not produce a download link');
        }

        const required = [
          'liteLoaded',
          'fileInputSurface',
          'exportBlobSurface',
          'languageSpanish',
          'duration15',
          'randomCheckbox',
          'localFileImportSynthetic',
          'randomRenderCompleted',
          'exportDownloadReady'
        ];
        result.passed = required.every((name) => result.checks[name] === true);
      } catch (error) {
        result.errors.push(error?.message || String(error));
      }
      return result;
    """
}
#else
import WebKit

enum LiteSmokeHarness {
    static func runIfNeeded(in webView: WKWebView) {}
}
#endif
