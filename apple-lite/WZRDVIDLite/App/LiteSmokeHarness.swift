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
        let fixtureAudioContext = null;
        let fixtureAudioDestination = null;
        const makeToneVideoFile = async (name, label, color, frequency, durationSeconds = 5) => {
          const fixtureCanvas = document.createElement('canvas');
          fixtureCanvas.width = 192;
          fixtureCanvas.height = 108;
          const fixtureContext = fixtureCanvas.getContext('2d');
          let stream = fixtureCanvas.captureStream(0);
          let fixtureVideoTracks = stream.getVideoTracks();
          let requestFixtureFrame = () => fixtureVideoTracks[0]?.requestFrame?.();
          if (typeof fixtureVideoTracks[0]?.requestFrame !== 'function') {
            fixtureVideoTracks.forEach((track) => track.stop?.());
            stream = fixtureCanvas.captureStream(15);
            fixtureVideoTracks = stream.getVideoTracks();
            requestFixtureFrame = () => {};
          }
          const Context = window.AudioContext || window.webkitAudioContext;
          if (frequency && !Context) throw new Error('AudioContext unavailable for source-audio fixture');
          if (frequency && !fixtureAudioContext) {
            fixtureAudioContext = new Context();
            fixtureAudioDestination = fixtureAudioContext.createMediaStreamDestination();
          }
          const context = frequency ? fixtureAudioContext : null;
          if (context?.state === 'suspended') await context.resume();
          const destination = frequency ? fixtureAudioDestination : null;
          const oscillator = context?.createOscillator?.() || null;
          const gain = context?.createGain?.() || null;
          if (oscillator && gain && destination) {
            oscillator.frequency.value = frequency;
            gain.gain.value = 0.22;
            oscillator.connect(gain);
            gain.connect(destination);
            const audioTrack = destination.stream.getAudioTracks()[0]?.clone?.();
            stream.addTrack(audioTrack);
          }
          const type = [
            'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
            'video/mp4',
            'video/webm;codecs=vp8,opus',
            'video/webm'
          ].find((candidate) => MediaRecorder.isTypeSupported(candidate)) || '';
          const chunks = [];
          const recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
          recorder.ondataavailable = (event) => {
            if (event.data?.size) chunks.push(event.data);
          };
          const stopped = new Promise((resolve) => { recorder.onstop = resolve; });
          const started = performance.now();
          recorder.start(250);
          oscillator?.start();
          while (performance.now() - started < durationSeconds * 1000) {
            const seconds = (performance.now() - started) / 1000;
            fixtureContext.fillStyle = color;
            fixtureContext.fillRect(0, 0, fixtureCanvas.width, fixtureCanvas.height);
            fixtureContext.fillStyle = '#fff1da';
            fixtureContext.font = '900 54px sans-serif';
            fixtureContext.fillText(label, 18, 68);
            fixtureContext.fillStyle = '#080706';
            fixtureContext.fillRect(80 + Math.sin(seconds * 4) * 46, 78, 42, 16);
            requestFixtureFrame();
            await sleep(50);
          }
          recorder.stop();
          await stopped;
          try { oscillator?.stop(); } catch {}
          stream.getTracks().forEach((track) => track.stop?.());
          const blobType = recorder.mimeType || type || 'video/mp4';
          return new File(chunks, name, { type: blobType });
        };

        const includeSourceAudio = document.querySelector('#includeSourceAudio');
        const resetButton = document.querySelector('#resetButton');
        const qualitySelect = document.querySelector('#qualitySelect');
        const ansiAmount = document.querySelector('#ansiAmount');
        check('liteLoaded', Boolean(mediaInput && audioInput && languageSelect && durationSelect && randomClip && includeSourceAudio && renderButton && downloadButton && canvas));
        check('fileInputSurface', Boolean(mediaInput && mediaInput.type === 'file' && mediaInput.accept.includes('video') && mediaInput.accept.includes('image')));
        check('includeSourceAudioDefaultOn', includeSourceAudio?.checked === true, String(includeSourceAudio?.checked));

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

        window.__WZRDVID_LITE_SMOKE_MODE = true;
        let sourceVideoA = null;
        let sourceVideoB = null;
        let sourceVideoC = null;
        let stillFile = null;
        let addAudioFile = null;
        if (result.capabilities.fileConstructor && result.capabilities.dataTransfer && result.capabilities.mediaRecorder && result.capabilities.captureStream) {
          sourceVideoA = await makeToneVideoFile('source-A-440.mp4', 'A', '#be245c', 440);
          sourceVideoB = await makeToneVideoFile('source-B-880.mp4', 'B', '#167a6c', 880);
          sourceVideoC = await makeToneVideoFile('source-C-silent.mp4', 'C', '#3f6594', 0);
          const addedToneMedia = await makeToneVideoFile('add-AUDIO-220-fixture.mp4', '+', '#3a327a', 220, 20);
          fixtureAudioDestination?.stream.getTracks().forEach((track) => track.stop?.());
          fixtureAudioDestination = null;
          await fixtureAudioContext?.close?.();
          fixtureAudioContext = null;
          const stillCanvas = document.createElement('canvas');
          stillCanvas.width = 192;
          stillCanvas.height = 108;
          const stillContext = stillCanvas.getContext('2d');
          stillContext.fillStyle = '#f2ca52';
          stillContext.fillRect(0, 0, 192, 108);
          stillContext.fillStyle = '#080706';
          stillContext.font = '900 34px sans-serif';
          stillContext.fillText('STILL', 30, 65);
          const stillBlob = await new Promise((resolve) => stillCanvas.toBlob(resolve, 'image/png'));
          stillFile = new File([stillBlob], 'source-STILL.png', { type: 'image/png' });
          addAudioFile = new File([addedToneMedia], 'add-AUDIO-220.m4a', { type: 'audio/mp4' });
          const transfer = new DataTransfer();
          transfer.items.add(sourceVideoA);
          transfer.items.add(stillFile);
          transfer.items.add(sourceVideoC);
          transfer.items.add(sourceVideoB);
          mediaInput.files = transfer.files;
          mediaInput.dispatchEvent(new Event('change', { bubbles: true }));
          for (let index = 0; index < 120; index += 1) {
            const content = fileList.textContent || '';
            if (content.includes(sourceVideoA.name) && content.includes(sourceVideoB.name) && content.includes(sourceVideoC.name) && content.includes(stillFile.name)) break;
            await sleep(100);
          }
          const importedText = fileList.textContent || '';
          check('localFileImportSynthetic', importedText.includes(sourceVideoA.name) && importedText.includes(sourceVideoB.name) && importedText.includes(sourceVideoC.name) && importedText.includes(stillFile.name), importedText);
          await sleep(1500);
        } else {
          check('localFileImportSynthetic', false, 'File/DataTransfer/MediaRecorder unavailable in WKWebView smoke context');
        }

        const armAddedAudio = async () => {
          const transfer = new DataTransfer();
          transfer.items.add(addAudioFile);
          audioInput.files = transfer.files;
          audioInput.dispatchEvent(new Event('change', { bubbles: true }));
          for (let index = 0; index < 60; index += 1) {
            if ((fileList.textContent || '').includes(addAudioFile.name)) return true;
            await sleep(100);
          }
          return false;
        };
        const renderMode = async (name, options) => {
          includeSourceAudio.checked = options.source;
          includeSourceAudio.dispatchEvent(new Event('change', { bubbles: true }));
          randomClip.checked = options.random;
          randomClip.dispatchEvent(new Event('change', { bubbles: true }));
          qualitySelect.value = options.quality;
          qualitySelect.dispatchEvent(new Event('change', { bubbles: true }));
          durationSelect.value = String(options.uiDuration);
          durationSelect.dispatchEvent(new Event('change', { bubbles: true }));
          if (options.overrideDuration) window.__WZRDVID_LITE_SMOKE_DURATION_SECONDS = options.overrideDuration;
          else delete window.__WZRDVID_LITE_SMOKE_DURATION_SECONDS;
          const priorFilename = window.WZRDVID_LITE_EXPORT?.diagnostics?.()?.filename || '';
          renderButton.click();
          for (let index = 0; index < 900; index += 1) {
            const diagnostics = window.WZRDVID_LITE_EXPORT?.diagnostics?.();
            if (diagnostics?.filename && diagnostics.filename !== priorFilename && !renderButton.disabled) break;
            await sleep(100);
          }
          const diagnostics = JSON.parse(JSON.stringify(window.WZRDVID_LITE_EXPORT?.diagnostics?.() || {}));
          let nativeExportSent = false;
          let nativeValidation = {};
          if (options.nativeExport && diagnostics.filename) {
            window.__wzrdvidNativeExportValidation = null;
            nativeExportSent = await window.WZRDVID_LITE_EXPORT?.shareRenderedClip?.();
            for (let index = 0; index < 50; index += 1) {
              if (window.__wzrdvidNativeExportValidation) break;
              await sleep(100);
            }
            nativeValidation = JSON.parse(JSON.stringify(window.__wzrdvidNativeExportValidation || {}));
          }
          return {
            name,
            diagnostics,
            nativeExportSent: Boolean(nativeExportSent),
            nativeValidation,
            runtime: JSON.parse(JSON.stringify(window.WZRDVID_LITE_EXPORT?.runtimeDiagnostics?.() || {}))
          };
        };

        if (result.checks.localFileImportSynthetic) {
          ansiAmount.value = '0';
          ansiAmount.dispatchEvent(new Event('input', { bubbles: true }));
          const modeB = await renderMode('source-on-no-add', { source: true, random: false, quality: 'fast', uiDuration: 15, overrideDuration: 1.5, nativeExport: true });
          const modeA = await renderMode('source-off-no-add', { source: false, random: false, quality: 'fast', uiDuration: 15, overrideDuration: 1.2, nativeExport: false });
          const audioArmed = await armAddedAudio();
          check('localAudioImportSynthetic', audioArmed, text('#fileList'));
          const modeC = await renderMode('source-off-add', { source: false, random: false, quality: 'fast', uiDuration: 15, overrideDuration: 1.5, nativeExport: true });
          const modeD = await renderMode('source-on-add', { source: true, random: true, quality: 'fast', uiDuration: 15, overrideDuration: null, nativeExport: true });
          const clearedAddedAudio = window.WZRDVID_LITE_TEST?.clearAddedAudio?.() === true;
          const modeBRepeat = await renderMode('source-on-no-add-repeat', { source: true, random: false, quality: 'better', uiDuration: 30, overrideDuration: null, nativeExport: true });
          result.modeResults = [modeB, modeA, modeC, modeD, modeBRepeat];
          result.audioMode = modeBRepeat.diagnostics.audioMode || '';
          result.exportDiagnostics = modeD.diagnostics;
          result.nativeExportSent = modeD.nativeExportSent;
          result.nativeExportValidation = modeD.nativeValidation;

          check('modeASilent', modeA.diagnostics.audioTracks === 0 && modeA.diagnostics.audioMode === 'none', JSON.stringify(modeA.diagnostics));
          check('modeBSourceOnly', modeB.diagnostics.audioTracks === 1 && modeB.diagnostics.sourceAudioReady === true && modeB.diagnostics.audioMode === 'sourceWebAudio', JSON.stringify(modeB.diagnostics));
          check('modeCAddedOnly', modeC.diagnostics.audioTracks === 1 && modeC.diagnostics.sourceAudioReady === false && ['captureStream', 'webAudio'].includes(modeC.diagnostics.audioMode), JSON.stringify(modeC.diagnostics));
          check('modeDMixed', modeD.diagnostics.audioTracks === 1 && modeD.diagnostics.sourceAudioReady === true && modeD.diagnostics.audioMode === 'mixedWebAudio', JSON.stringify(modeD.diagnostics));
          check('repeatedRenderSourceAgain', modeBRepeat.diagnostics.audioTracks === 1 && modeBRepeat.diagnostics.sourceNodesCreated === 0 && modeBRepeat.diagnostics.audioMode === 'sourceWebAudio', JSON.stringify(modeBRepeat.diagnostics));
          check('repeatedRenderNativeAudio', modeBRepeat.nativeExportSent === true && Number(modeBRepeat.nativeValidation.audioTracks || 0) === 1, JSON.stringify(modeBRepeat.nativeValidation));
          check('singleAudioContext', modeBRepeat.runtime.contextCount === 1, JSON.stringify(modeBRepeat.runtime));
          check('noDuplicateAudioConnections', modeBRepeat.runtime.activeControllers === 0 && modeBRepeat.runtime.activeConnections === 0, JSON.stringify(modeBRepeat.runtime));
          check('sourceSwitchesObserved', Number(modeD.diagnostics.sourceSwitchCount || 0) >= 2, JSON.stringify(modeD.diagnostics));
          check('randomRenderCompleted', Boolean(modeD.diagnostics.filename), JSON.stringify(modeD.diagnostics));
          check('exportDownloadReady', Boolean(modeBRepeat.diagnostics.filename?.includes('wzrdvid-lite-30s')), modeBRepeat.diagnostics.filename || '');
          check('nativeRenderedClipReady', Boolean(window.WZRDVID_LITE_EXPORT?.hasRenderedClip?.()), 'native rendered clip payload unavailable');
          check('audioPipelineReady', ['sourceWebAudio', 'mixedWebAudio'].includes(modeD.diagnostics.audioMode), modeD.diagnostics.audioMode || 'no audio mode');
          check('smoothFpsTarget', Number(modeD.diagnostics.targetFps || 0) >= 30, JSON.stringify(modeD.diagnostics));
          check('betterQuality24Fps', Number(modeBRepeat.diagnostics.targetFps || 0) === 24, JSON.stringify(modeBRepeat.diagnostics));
          check('duration30Rendered', Number(modeBRepeat.diagnostics.renderDuration || 0) === 30, JSON.stringify(modeBRepeat.diagnostics));
          check('exportHasVideoTrack', Number(modeD.diagnostics.videoTracks || 0) > 0, JSON.stringify(modeD.diagnostics));
          check('exportBlobHasBytes', Number(modeD.diagnostics.blobSize || 0) > 1024, JSON.stringify(modeD.diagnostics));
          check('randomTimelineUsesMultipleSources', Number(modeD.diagnostics.timelineSources || 0) >= 3, JSON.stringify(modeD.diagnostics));
          check('nativeExportSent', modeD.nativeExportSent === true, 'native export bridge did not accept mixed payload');
          check('nativeExportValidatedVideo', Number(modeD.nativeValidation.videoTracks || 0) > 0, JSON.stringify(modeD.nativeValidation));
          check('nativeExportValidatedAudio', Number(modeD.nativeValidation.audioTracks || 0) === 1, JSON.stringify(modeD.nativeValidation));
          check('addedAudioCanClearInSmoke', clearedAddedAudio === true && modeBRepeat.diagnostics.addedAudio === false, JSON.stringify(modeBRepeat.diagnostics));
          check('repeatedRenderNoMediaElementError', !/InvalidStateError|already connected|HTMLMediaElement previously/i.test(text('#logOutput')), text('#logOutput'));

          durationSelect.value = '60';
          durationSelect.dispatchEvent(new Event('change', { bubbles: true }));
          check('duration60StateReady', durationSelect.value === '60' && /60/.test(renderButton.textContent || ''), renderButton.textContent || '');
          window.__WZRDVID_LITE_SMOKE_DURATION_SECONDS = 5;
          includeSourceAudio.checked = true;
          renderButton.click();
          await sleep(500);
          resetButton.click();
          for (let index = 0; index < 30; index += 1) {
            if (!window.WZRDVID_LITE_EXPORT?.runtimeDiagnostics?.()?.activeRender) break;
            await sleep(100);
          }
          result.runtimeAfterClear = JSON.parse(JSON.stringify(window.WZRDVID_LITE_EXPORT?.runtimeDiagnostics?.() || {}));
          check('clearProjectStopsAudioGraph', result.runtimeAfterClear.activeRender === false && result.runtimeAfterClear.activeControllers === 0 && result.runtimeAfterClear.activeConnections === 0, JSON.stringify(result.runtimeAfterClear));
          check('clearProjectRemovesMedia', !(fileList.textContent || '').includes(sourceVideoA.name) && !window.WZRDVID_LITE_EXPORT?.hasRenderedClip?.(), text('#fileList'));
          check('clearProjectKeepsSourceDefault', includeSourceAudio.checked === true, String(includeSourceAudio.checked));
        } else {
          check('localAudioImportSynthetic', false, 'source fixtures did not import');
        }

        const required = [
          'liteLoaded',
          'fileInputSurface',
          'includeSourceAudioDefaultOn',
          'exportBlobSurface',
          'languageSpanish',
          'duration15',
          'randomCheckbox',
          'localFileImportSynthetic',
          'localAudioImportSynthetic',
          'modeASilent',
          'modeBSourceOnly',
          'modeCAddedOnly',
          'modeDMixed',
          'repeatedRenderSourceAgain',
          'repeatedRenderNativeAudio',
          'singleAudioContext',
          'noDuplicateAudioConnections',
          'sourceSwitchesObserved',
          'randomRenderCompleted',
          'exportDownloadReady',
          'nativeExportBridgeSurface',
          'nativeRenderedClipReady',
          'audioPipelineReady',
          'smoothFpsTarget',
          'betterQuality24Fps',
          'duration30Rendered',
          'duration60StateReady',
          'exportHasVideoTrack',
          'exportBlobHasBytes',
          'randomTimelineUsesMultipleSources',
          'nativeExportSent',
          'nativeExportValidatedVideo',
          'nativeExportValidatedAudio',
          'addedAudioCanClearInSmoke',
          'repeatedRenderNoMediaElementError',
          'clearProjectStopsAudioGraph',
          'clearProjectRemovesMedia',
          'clearProjectKeepsSourceDefault'
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
