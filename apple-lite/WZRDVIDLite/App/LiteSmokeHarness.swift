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
        const audioInput = document.querySelector('#audioInput');
        const fileList = document.querySelector('#fileList');
        const canvas = document.querySelector('#previewCanvas');
        const makeToneWavFile = () => {
          const sampleRate = 8000;
          const seconds = 1;
          const samples = sampleRate * seconds;
          const buffer = new ArrayBuffer(44 + samples * 2);
          const view = new DataView(buffer);
          const write = (offset, text) => {
            for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
          };
          write(0, 'RIFF');
          view.setUint32(4, 36 + samples * 2, true);
          write(8, 'WAVE');
          write(12, 'fmt ');
          view.setUint32(16, 16, true);
          view.setUint16(20, 1, true);
          view.setUint16(22, 1, true);
          view.setUint32(24, sampleRate, true);
          view.setUint32(28, sampleRate * 2, true);
          view.setUint16(32, 2, true);
          view.setUint16(34, 16, true);
          write(36, 'data');
          view.setUint32(40, samples * 2, true);
          for (let i = 0; i < samples; i += 1) {
            const sample = Math.sin((i / sampleRate) * 440 * Math.PI * 2) * 0.25;
            view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, sample)) * 32767, true);
          }
          return new File([buffer], 'lite-smoke-tone.wav', { type: 'audio/wav' });
        };

        check('liteLoaded', Boolean(mediaInput && audioInput && languageSelect && durationSelect && randomClip && renderButton && downloadButton && canvas));
        check('fileInputSurface', Boolean(mediaInput && mediaInput.type === 'file' && mediaInput.accept.includes('video') && mediaInput.accept.includes('image')));

        result.capabilities.fileConstructor = typeof File === 'function';
        result.capabilities.dataTransfer = typeof DataTransfer === 'function';
        result.capabilities.blob = typeof Blob === 'function';
        result.capabilities.objectURL = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function';
        result.capabilities.mediaRecorder = typeof MediaRecorder === 'function';
        result.capabilities.captureStream = typeof canvas?.captureStream === 'function';
        result.capabilities.navigatorShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
        result.capabilities.nativeExportBridge = Boolean(window.webkit?.messageHandlers?.wzrdvidExport);
        result.capabilities.audioCaptureStream = typeof Audio !== 'undefined' && typeof Audio.prototype.captureStream === 'function';
        result.capabilities.audioContext = typeof AudioContext === 'function' || typeof webkitAudioContext === 'function';
        result.capabilities.mediaStreamDestination = (() => {
          const Context = window.AudioContext || window.webkitAudioContext;
          if (!Context) return false;
          try {
            const context = new Context();
            const supported = typeof context.createMediaStreamDestination === 'function';
            context.close?.();
            return supported;
          } catch {
            return false;
          }
        })();
        check('exportBlobSurface', Boolean(result.capabilities.blob && result.capabilities.objectURL && downloadButton && 'download' in downloadButton));
        check('nativeExportBridgeSurface', Boolean(result.capabilities.nativeExportBridge && window.WZRDVID_LITE_EXPORT?.shareRenderedClip), 'native export bridge unavailable');

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
          const secondFile = new File([bytes], 'lite-smoke-second.png', { type: 'image/png' });
          const transfer = new DataTransfer();
          transfer.items.add(file);
          transfer.items.add(secondFile);
          mediaInput.files = transfer.files;
          mediaInput.dispatchEvent(new Event('change', { bubbles: true }));
          for (let index = 0; index < 80; index += 1) {
            if ((fileList.textContent || '').includes('lite-smoke.png') && (fileList.textContent || '').includes('lite-smoke-second.png')) break;
            await sleep(100);
          }
          check('localFileImportSynthetic', (fileList.textContent || '').includes('lite-smoke.png') && (fileList.textContent || '').includes('lite-smoke-second.png'), text('#fileList'));
          const audioTransfer = new DataTransfer();
          audioTransfer.items.add(makeToneWavFile());
          audioInput.files = audioTransfer.files;
          audioInput.dispatchEvent(new Event('change', { bubbles: true }));
          for (let index = 0; index < 60; index += 1) {
            if ((fileList.textContent || '').includes('lite-smoke-tone.wav')) break;
            await sleep(100);
          }
          check('localAudioImportSynthetic', (fileList.textContent || '').includes('lite-smoke-tone.wav'), text('#fileList'));
        } else {
          check('localFileImportSynthetic', false, 'File/DataTransfer unavailable in WKWebView smoke context');
          check('localAudioImportSynthetic', false, 'File/DataTransfer unavailable in WKWebView smoke context');
        }

        if (result.checks.localFileImportSynthetic && result.capabilities.mediaRecorder && result.capabilities.captureStream) {
          renderButton.click();
          for (let index = 0; index < 360; index += 1) {
            if ((downloadButton.getAttribute('href') || '').startsWith('blob:')) break;
            await sleep(100);
          }
          check('randomRenderCompleted', (downloadButton.getAttribute('href') || '').startsWith('blob:'), text('#statusLine'));
          check('exportDownloadReady', Boolean(downloadButton.download && downloadButton.download.includes('wzrdvid-lite-15s')), downloadButton.download || '');
          check('nativeRenderedClipReady', Boolean(window.WZRDVID_LITE_EXPORT?.hasRenderedClip?.()), 'native rendered clip payload unavailable');
          const audioMode = window.WZRDVID_LITE_EXPORT?.audioMode?.() || '';
          result.audioMode = audioMode;
          check('audioPipelineReady', ['captureStream', 'webAudio'].includes(audioMode), audioMode || 'no audio mode');
          const diagnostics = window.WZRDVID_LITE_EXPORT?.diagnostics?.() || {};
          result.exportDiagnostics = diagnostics;
          check('smoothFpsTarget', Number(diagnostics.targetFps || 0) >= 30, JSON.stringify(diagnostics));
          check('exportHasVideoTrack', Number(diagnostics.videoTracks || 0) > 0, JSON.stringify(diagnostics));
          check('exportBlobHasBytes', Number(diagnostics.blobSize || 0) > 1024, JSON.stringify(diagnostics));
          check('randomTimelineUsesMultipleSources', Number(diagnostics.timelineSources || 0) >= 2, JSON.stringify(diagnostics));
          window.__wzrdvidNativeExportValidation = null;
          const nativeExportSent = await window.WZRDVID_LITE_EXPORT?.shareRenderedClip?.();
          result.nativeExportSent = Boolean(nativeExportSent);
          for (let index = 0; index < 30; index += 1) {
            if (window.__wzrdvidNativeExportValidation) break;
            await sleep(100);
          }
          const nativeValidation = window.__wzrdvidNativeExportValidation || {};
          result.nativeExportValidation = nativeValidation;
          check('nativeExportSent', nativeExportSent === true, 'native export bridge did not accept payload');
          check('nativeExportValidatedVideo', Number(nativeValidation.videoTracks || 0) > 0, JSON.stringify(nativeValidation));
        } else {
          check('randomRenderCompleted', false, 'MediaRecorder/canvas capture unavailable or local import failed');
          check('exportDownloadReady', false, 'Render did not produce a download link');
          check('nativeRenderedClipReady', false, 'Render did not produce a native export payload');
          check('audioPipelineReady', false, 'Render did not run');
          check('smoothFpsTarget', false, 'Render did not run');
          check('exportHasVideoTrack', false, 'Render did not run');
          check('exportBlobHasBytes', false, 'Render did not run');
          check('randomTimelineUsesMultipleSources', false, 'Render did not run');
          check('nativeExportSent', false, 'Render did not run');
          check('nativeExportValidatedVideo', false, 'Render did not run');
        }

        const required = [
          'liteLoaded',
          'fileInputSurface',
          'exportBlobSurface',
          'languageSpanish',
          'duration15',
          'randomCheckbox',
          'localFileImportSynthetic',
          'localAudioImportSynthetic',
          'randomRenderCompleted',
          'exportDownloadReady',
          'nativeExportBridgeSurface',
          'nativeRenderedClipReady',
          'audioPipelineReady',
          'smoothFpsTarget',
          'exportHasVideoTrack',
          'exportBlobHasBytes',
          'randomTimelineUsesMultipleSources',
          'nativeExportSent',
          'nativeExportValidatedVideo'
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
