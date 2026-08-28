(() => {
  'use strict';

  const chaos = window.WZRDVID_LITE_CHAOS;
  if (!chaos) throw new Error('WZRD.VID Lite deterministic chaos contract failed to load');

  const DEFAULT_DURATION = 30;
  const LITE_FAST_FPS = 30;
  const LITE_BETTER_FPS = 24;
  const LITE_PRESET_FPS_CAP = 30;
  const SOURCE_AUDIO_RAMP_SECONDS = 0.018;
  const VIDEO_EXTENSIONS = new Set(['mp4', 'mov', 'm4v', 'mts', 'm2ts', 'webm', 'mkv', 'avi']);
  const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp', 'avif', 'gif', 'bmp', 'tif', 'tiff', 'heic', 'heif']);
  const AUDIO_EXTENSIONS = new Set(['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'opus', 'aif', 'aiff']);

  const presets = {
    'Chunkcore Chaos': { grid: 74, ramp: '  ░▒▓█', scanlines: 0.34, rgb: 5, tape: 0.34, mosaic: 0.4, punch: 0.28, fps: LITE_PRESET_FPS_CAP },
    'Classic ANSI Lite': { grid: 96, ramp: ' .:-=+*#%@', scanlines: 0.2, rgb: 2, tape: 0.12, mosaic: 0.14, punch: 0.16, fps: LITE_PRESET_FPS_CAP },
    'VHS Damage Lite': { grid: 84, ramp: '  ░▒▓█', scanlines: 0.46, rgb: 8, tape: 0.58, mosaic: 0.26, punch: 0.22, fps: LITE_PRESET_FPS_CAP },
    'Dial-Up Glitch': { grid: 68, ramp: '  ░▒▓█', scanlines: 0.28, rgb: 9, tape: 0.44, mosaic: 0.62, punch: 0.36, fps: LITE_PRESET_FPS_CAP },
    'PUBLIC ACCESS': { grid: 88, ramp: ' .:-=+*#%@ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', scanlines: 0.38, rgb: 4, tape: 0.5, mosaic: 0.18, punch: 0.14, fps: LITE_PRESET_FPS_CAP, profile: 'publicAccess' }
  };

  const state = {
    media: [],
    audio: null,
    renderedUrl: null,
    renderedBlob: null,
    renderedFilename: '',
    renderedType: '',
    lastAudioMode: 'none',
    lastExportDiagnostics: null,
    lastPlanOracle: null,
    projectSeed: null,
    renderAbort: false,
    activeRenderSession: null
  };

  const audioRuntime = {
    context: null,
    contextCount: 0,
    mediaElementSources: new WeakMap(),
    totalSourceNodes: 0,
    activeControllers: 0,
    activeConnections: 0
  };

  const elements = {
    mediaDrop: document.getElementById('mediaDrop'),
    mediaInput: document.getElementById('mediaInput'),
    mediaButton: document.getElementById('mediaButton'),
    audioDrop: document.getElementById('audioDrop'),
    audioInput: document.getElementById('audioInput'),
    audioButton: document.getElementById('audioButton'),
    resetButton: document.getElementById('resetButton'),
    fileList: document.getElementById('fileList'),
    preset: document.getElementById('presetSelect'),
    strength: document.getElementById('effectStrength'),
    ansi: document.getElementById('ansiAmount'),
    ansiValue: document.getElementById('ansiValue'),
    density: document.getElementById('ansiDensity'),
    duration: document.getElementById('durationSelect'),
    randomClip: document.getElementById('randomClipAssembly'),
    rerollChaos: document.getElementById('rerollChaos'),
    chaosSeedStatus: document.getElementById('chaosSeedStatus'),
    includeSourceAudio: document.getElementById('includeSourceAudio'),
    quality: document.getElementById('qualitySelect'),
    renderButton: document.getElementById('renderButton'),
    downloadButton: document.getElementById('downloadButton'),
    canvas: document.getElementById('previewCanvas'),
    progress: document.querySelector('#progressBar span'),
    status: document.getElementById('statusLine'),
    log: document.getElementById('logOutput')
  };

  const ctx = elements.canvas.getContext('2d', { willReadFrequently: true });
  const ansiCanvas = document.createElement('canvas');
  const ansiCtx = ansiCanvas.getContext('2d', { willReadFrequently: true });
  const tempCanvas = document.createElement('canvas');
  const tempCtx = tempCanvas.getContext('2d', { willReadFrequently: true });

  function t(key, values = {}) {
    return window.WZRD_I18N ? window.WZRD_I18N.t(key, values) : key;
  }

  function log(message) {
    const line = `[${new Date().toLocaleTimeString()}] ${message}`;
    elements.log.textContent += `\n${line}`;
    elements.log.scrollTop = elements.log.scrollHeight;
  }

  function setStatus(message) {
    elements.status.textContent = message;
  }

  function setProgress(value) {
    elements.progress.style.width = `${Math.max(0, Math.min(100, value))}%`;
  }

  function generateProjectSeed() {
    if (!window.crypto?.getRandomValues) {
      throw new Error(t('lite.log_crypto_unavailable'));
    }
    return window.crypto.getRandomValues(new Uint32Array(1))[0] >>> 0;
  }

  function updateChaosUi() {
    const armed = state.projectSeed !== null;
    elements.rerollChaos.disabled = !armed || Boolean(state.activeRenderSession);
    elements.chaosSeedStatus.textContent = armed
      ? t('lite.chaos_armed', { seed: chaos.seedLabel(state.projectSeed) })
      : t('lite.chaos_unarmed');
  }

  function ensureProjectSeed() {
    if (state.projectSeed !== null) return state.projectSeed;
    state.projectSeed = generateProjectSeed();
    updateChaosUi();
    log(t('lite.log_chaos_armed', { seed: chaos.seedLabel(state.projectSeed) }));
    return state.projectSeed;
  }

  function rerollChaos() {
    if (state.projectSeed === null || state.activeRenderSession) return;
    const previousSeed = state.projectSeed;
    do {
      state.projectSeed = generateProjectSeed();
    } while (state.projectSeed === previousSeed);
    state.lastPlanOracle = null;
    updateChaosUi();
    log(t('lite.log_chaos_rerolled', { seed: chaos.seedLabel(state.projectSeed) }));
  }

  function extensionOf(file) {
    return (file.name.split('.').pop() || '').toLowerCase();
  }

  function isHeicFile(file) {
    const ext = extensionOf(file);
    return ext === 'heic' || ext === 'heif' || /heic|heif/i.test(file.type || '');
  }

  function fileKind(file) {
    const ext = extensionOf(file);
    if (file.type.startsWith('video/') || VIDEO_EXTENSIONS.has(ext)) return 'video';
    if (file.type.startsWith('image/') || IMAGE_EXTENSIONS.has(ext)) return 'image';
    if (file.type.startsWith('audio/') || AUDIO_EXTENSIONS.has(ext)) return 'audio';
    return 'unknown';
  }

  function pickRecorderMimeType() {
    const candidates = [
      'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
      'video/mp4',
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm'
    ];
    return candidates.find((type) => window.MediaRecorder && MediaRecorder.isTypeSupported(type)) || '';
  }

  function revokeRenderedUrl() {
    if (state.renderedUrl) URL.revokeObjectURL(state.renderedUrl);
    state.renderedUrl = null;
    state.renderedBlob = null;
    state.renderedFilename = '';
    state.renderedType = '';
    state.lastExportDiagnostics = null;
  }

  function resetDownloadButton() {
    elements.downloadButton.className = 'btn btn-disabled';
    elements.downloadButton.removeAttribute('href');
    elements.downloadButton.removeAttribute('download');
    elements.downloadButton.setAttribute('aria-disabled', 'true');
    elements.downloadButton.textContent = t('lite.download_clip');
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('blob read failed'));
      reader.readAsDataURL(blob);
    });
  }

  async function shareRenderedClipWithNative() {
    const bridge = window.webkit?.messageHandlers?.wzrdvidExport;
    if (!bridge || !state.renderedBlob) return false;

    const dataUrl = await blobToDataUrl(state.renderedBlob);
    const base64Marker = ';base64,';
    const markerIndex = dataUrl.indexOf(base64Marker);
    const base64 = markerIndex >= 0
      ? dataUrl.slice(markerIndex + base64Marker.length)
      : dataUrl.slice(dataUrl.lastIndexOf(',') + 1);
    const entropy = window.crypto?.getRandomValues
      ? window.crypto.getRandomValues(new Uint32Array(1))[0].toString(16)
      : Date.now().toString(16);
    const id = `export-${Date.now()}-${entropy}`;
    const chunkSize = 48 * 1024;
    const chunkCount = Math.max(1, Math.ceil(base64.length / chunkSize));
    bridge.postMessage({
      action: 'start',
      id,
      filename: state.renderedFilename || 'wzrdvid-lite.mp4',
      mimeType: state.renderedBlob.type || state.renderedType || 'video/mp4',
      chunkCount
    });
    for (let index = 0; index < chunkCount; index += 1) {
      bridge.postMessage({
        action: 'chunk',
        id,
        index,
        data: base64.slice(index * chunkSize, (index + 1) * chunkSize)
      });
    }
    bridge.postMessage({ action: 'finish', id });
    return true;
  }

  window.WZRDVID_LITE_EXPORT = {
    hasRenderedClip: () => Boolean(state.renderedBlob && state.renderedFilename),
    audioMode: () => state.lastAudioMode,
    diagnostics: () => state.lastExportDiagnostics,
    runtimeDiagnostics: () => audioRuntimeDiagnostics(),
    shareRenderedClip: shareRenderedClipWithNative
  };

  window.WZRDVID_LITE_TEST = {
    clearAddedAudio: () => {
      if (!window.__WZRDVID_LITE_SMOKE_MODE) return false;
      clearAddedAudio();
      return true;
    },
    projectState: () => ({
      projectSeed: state.projectSeed,
      seedLabel: chaos.seedLabel(state.projectSeed),
      mediaCount: state.media.length,
      planOracle: state.lastPlanOracle
    })
  };

  function audioRuntimeDiagnostics() {
    return {
      contextCount: audioRuntime.contextCount,
      contextState: audioRuntime.context?.state || 'none',
      totalSourceNodes: audioRuntime.totalSourceNodes,
      activeControllers: audioRuntime.activeControllers,
      activeConnections: audioRuntime.activeConnections,
      activeRender: Boolean(state.activeRenderSession)
    };
  }

  function requestSharedAudioContext() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return { context: null, ready: Promise.resolve(false) };
    if (!audioRuntime.context) {
      try {
        audioRuntime.context = new AudioContext();
        audioRuntime.contextCount += 1;
      } catch {
        return { context: null, ready: Promise.resolve(false) };
      }
    }
    const context = audioRuntime.context;
    if (context.state === 'closed') return { context: null, ready: Promise.resolve(false) };
    const ready = context.state === 'suspended'
      ? context.resume().then(() => true).catch(() => false)
      : Promise.resolve(true);
    return { context, ready };
  }

  function cachedMediaElementSource(context, element) {
    const cached = audioRuntime.mediaElementSources.get(element);
    if (cached) return { node: cached.outlet, created: false };
    const source = context.createMediaElementSource(element);
    const outlet = context.createGain();
    outlet.gain.value = 1;
    source.connect(outlet);
    audioRuntime.mediaElementSources.set(element, { source, outlet });
    audioRuntime.totalSourceNodes += 1;
    return { node: outlet, created: true };
  }

  function releaseMediaElementSource(element) {
    const cached = element && audioRuntime.mediaElementSources.get(element);
    if (!cached) return;
    try { cached.source.disconnect(); } catch { /* source may already be detached */ }
    try { cached.outlet.disconnect(); } catch { /* outlet may already be detached */ }
    audioRuntime.mediaElementSources.delete(element);
  }

  function clearAddedAudio() {
    if (!state.audio) return;
    for (const element of [state.audio.audio, state.audio.mixElement]) {
      if (!element) continue;
      releaseMediaElementSource(element);
      try { element.pause(); } catch { /* audio may already be stopped */ }
      try { element.src = ''; } catch { /* ignore source cleanup failures */ }
    }
    if (state.audio.url) URL.revokeObjectURL(state.audio.url);
    state.audio = null;
    updateFileList();
  }

  async function addMediaFiles(files) {
    const startedAt = performance.now();
    const selectedFiles = Array.from(files || []);
    const accepted = [];
    let heicCount = 0;
    for (const file of selectedFiles) {
      const kind = fileKind(file);
      if (kind === 'video' || kind === 'image') {
        if (kind === 'image' && isHeicFile(file)) heicCount += 1;
        accepted.push({ file, kind });
      }
      if (kind === 'audio') await setAudioFile(file);
    }
    if (!accepted.length) {
      log(t('lite.log_no_timeline'));
      return;
    }
    let loaded = 0;
    let failed = 0;
    for (const item of accepted) {
      try {
        const prepared = await prepareTimelineItem(item.file, item.kind);
        state.media.push(prepared);
        loaded += 1;
        log(t('lite.log_loaded', { kind: t(`lite.kind.${item.kind}`), name: item.file.name }));
        if (prepared.isHeic) {
          log(t('lite.log_heic_decode_profile', { name: item.file.name, seconds: (prepared.prepareMs / 1000).toFixed(2) }));
        }
      } catch (error) {
        failed += 1;
        log(t('lite.log_decode_failed', { name: item.file.name, error: error.message || error }));
      }
    }
    log(t('lite.log_import_profile', {
      count: accepted.length,
      loaded,
      failed,
      heic: heicCount,
      seconds: ((performance.now() - startedAt) / 1000).toFixed(2)
    }));
    if (loaded > 0 && state.projectSeed === null) {
      try {
        ensureProjectSeed();
      } catch (error) {
        log(error?.message || String(error));
      }
    }
    updateFileList();
    drawIdleFrame();
  }

  async function setAudioFile(file) {
    const kind = fileKind(file);
    if (kind !== 'audio' && kind !== 'video') {
      log(t('lite.log_audio_ignored', { name: file.name }));
      return;
    }
    clearAddedAudio();
    const url = URL.createObjectURL(file);
    const audio = new Audio(url);
    audio.preload = 'metadata';
    state.audio = { file, url, audio, mixElement: null, decodedContext: null, decodedBuffer: null, decodePromise: null };
    log(t('lite.log_audio_armed', { name: file.name }));
    updateFileList();
  }

  async function prepareTimelineItem(file, kind) {
    const startedAt = performance.now();
    const url = URL.createObjectURL(file);
    if (kind === 'video') {
      const video = document.createElement('video');
      video.src = url;
      video.muted = true;
      video.playsInline = true;
      video.preload = 'auto';
      try {
        await waitForMetadata(video);
        if (!Number.isFinite(video.duration) || video.duration <= 0) {
          throw new Error('video codec/container is not supported by this browser');
        }
      } catch (error) {
        URL.revokeObjectURL(url);
        throw error;
      }
      return { file, kind, url, element: video, duration: video.duration, prepareMs: performance.now() - startedAt, isHeic: false };
    }
    const image = new Image();
    image.decoding = 'async';
    image.src = url;
    try {
      await image.decode();
      if (!(image.naturalWidth > 0 && image.naturalHeight > 0)) {
        throw new Error('image format is not supported by this browser');
      }
    } catch (error) {
      URL.revokeObjectURL(url);
      throw error;
    }
    return { file, kind, url, element: image, duration: 2.4, prepareMs: performance.now() - startedAt, isHeic: isHeicFile(file) };
  }

  function clearProject() {
    state.renderAbort = true;
    state.activeRenderSession?.abort?.();
    state.media.forEach((item) => {
      releaseMediaElementSource(item.element);
      try { item.element?.pause?.(); } catch { /* media may already be stopped */ }
      try { item.element.muted = true; } catch { /* images do not expose muted */ }
      try {
        if (item.element && 'src' in item.element) item.element.src = '';
      } catch { /* ignore source cleanup failures */ }
      if (item.url) URL.revokeObjectURL(item.url);
    });
    clearAddedAudio();
    revokeRenderedUrl();
    state.media = [];
    state.lastAudioMode = 'none';
    state.projectSeed = null;
    state.lastPlanOracle = null;
    if ('lastExportDiagnostics' in state) state.lastExportDiagnostics = null;
    if (elements.mediaInput) elements.mediaInput.value = '';
    if (elements.audioInput) elements.audioInput.value = '';
    resetDownloadButton();
    setProgress(0);
    elements.log.textContent = t('lite.log_initial');
    log(t('lite.log_project_cleared'));
    setStatus(t('lite.status_cleared'));
    updateChaosUi();
    updateFileList();
    drawIdleFrame();
  }

  function waitForMetadata(media) {
    return new Promise((resolve, reject) => {
      if (Number.isFinite(media.duration) && media.duration > 0) {
        resolve();
        return;
      }
      media.onloadedmetadata = () => resolve();
      media.onerror = () => reject(new Error('metadata failed'));
    });
  }

  function waitForPlayable(media, timeoutMs = 1500, reload = false) {
    return new Promise((resolve) => {
      if (reload) {
        try { media.load?.(); } catch { /* continue to the bounded readiness wait */ }
      }
      if (media.readyState >= 2) {
        resolve(true);
        return;
      }
      let settled = false;
      const done = (ready) => {
        if (settled) return;
        settled = true;
        media.removeEventListener('canplay', onReady);
        media.removeEventListener('loadeddata', onReady);
        media.removeEventListener('error', onError);
        resolve(ready);
      };
      const onReady = () => done(true);
      const onError = () => done(false);
      media.addEventListener('canplay', onReady, { once: true });
      media.addEventListener('loadeddata', onReady, { once: true });
      media.addEventListener('error', onError, { once: true });
      setTimeout(() => done(media.readyState >= 2), timeoutMs);
    });
  }

  function seekVideo(video, time) {
    return new Promise((resolve) => {
      const target = Math.max(0, Math.min(time, Math.max(0, (video.duration || 0) - 0.05)));
      if (Math.abs((video.currentTime || 0) - target) < 0.035 && video.readyState >= 2) {
        resolve();
        return;
      }
      const done = () => {
        video.removeEventListener('seeked', done);
        resolve();
      };
      video.addEventListener('seeked', done, { once: true });
      video.currentTime = target;
      setTimeout(done, 450);
    });
  }

  function waitForVideoFrame(video) {
    return new Promise((resolve) => {
      if (video.readyState >= 2 && typeof video.requestVideoFrameCallback !== 'function') {
        resolve();
        return;
      }
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        resolve();
      };
      if (typeof video.requestVideoFrameCallback === 'function') {
        video.requestVideoFrameCallback(done);
      } else {
        video.addEventListener('loadeddata', done, { once: true });
      }
      setTimeout(done, 260);
    });
  }

  function updateFileList() {
    const lines = [];
    state.media.forEach((item, index) => {
      const duration = item.kind === 'video' ? `${(item.duration || 0).toFixed(1)}s` : t('lite.file_duration_hold');
      lines.push(`<li>${index + 1}. ${escapeHtml(item.file.name)} <span>// ${escapeHtml(t(`lite.kind.${item.kind}`))} // ${escapeHtml(duration)}</span></li>`);
    });
    if (state.audio) lines.push(`<li>${escapeHtml(t('lite.kind.audio').toUpperCase())}. ${escapeHtml(state.audio.file.name)} <span>// ${escapeHtml(t('lite.file_audio_bus'))}</span></li>`);
    elements.fileList.innerHTML = lines.join('') || `<li>${escapeHtml(t('lite.no_media'))}</li>`;
  }

  function escapeHtml(value) {
    return value.replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  }

  function selectedDuration() {
    const smokeOverride = Number(window.__WZRDVID_LITE_SMOKE_DURATION_SECONDS);
    if (window.__WZRDVID_LITE_SMOKE_MODE && Number.isFinite(smokeOverride) && smokeOverride > 0 && smokeOverride <= 60) {
      return smokeOverride;
    }
    const value = Number(elements.duration?.value || DEFAULT_DURATION);
    return [15, 30, 60].includes(value) ? value : DEFAULT_DURATION;
  }

  function updateRenderButtonCopy() {
    elements.renderButton.textContent = t('lite.make_clip', { seconds: selectedDuration() });
  }

  function updateLocalizedRuntimeText() {
    document.querySelectorAll('#durationSelect option').forEach((option) => {
      option.textContent = t('lite.sec', { seconds: option.value });
    });
    updateRenderButtonCopy();
    if (!state.renderedUrl) {
      resetDownloadButton();
    }
    if (!state.media.length) {
      setStatus(t('lite.status_idle'));
    }
    updateChaosUi();
    updateFileList();
    drawIdleFrame();
  }

  function isAnsiTime(time, intervals) {
    return intervals.some(([start, end]) => time >= start && time < end);
  }

  function qualitySettings() {
    if (elements.quality.value === 'better') return { width: 1280, height: 720, fps: LITE_BETTER_FPS };
    return { width: 854, height: 480, fps: LITE_FAST_FPS };
  }

  function drawIdleFrame() {
    const { width, height } = qualitySettings();
    resizeCanvas(width, height);
    ctx.fillStyle = '#080706';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#a9f4cb';
    ctx.font = `900 ${Math.max(24, width / 28)}px ui-monospace, monospace`;
    ctx.fillText(t('lite.canvas_title'), width * 0.06, height * 0.42);
    ctx.fillStyle = '#f4a6cf';
    ctx.font = `800 ${Math.max(14, width / 54)}px ui-monospace, monospace`;
    ctx.fillText(t('lite.canvas_subtitle'), width * 0.06, height * 0.52);
    drawScanlines(0.24);
  }

  function resizeCanvas(width, height) {
    if (elements.canvas.width !== width || elements.canvas.height !== height) {
      elements.canvas.width = width;
      elements.canvas.height = height;
    }
    tempCanvas.width = width;
    tempCanvas.height = height;
  }

  async function renderClip() {
    if (!state.media.length) {
      log(t('lite.log_add_before_render'));
      return;
    }
    if (!window.MediaRecorder || !elements.canvas.captureStream) {
      log(t('lite.log_mediarecorder_missing'));
      return;
    }
    let projectSeed;
    try {
      projectSeed = ensureProjectSeed();
    } catch (error) {
      log(error?.message || String(error));
      return;
    }

    const includeSourceAudio = Boolean(elements.includeSourceAudio?.checked);
    const sourceAudioRequested = includeSourceAudio && state.media.some((item) => item.kind === 'video');
    const addedAudioCaptureStream = state.audio && (state.audio.audio.captureStream || state.audio.audio.mozCaptureStream);
    const audioRequest = (sourceAudioRequested || (state.audio && !addedAudioCaptureStream))
      ? requestSharedAudioContext()
      : { context: null, ready: Promise.resolve(false) };

    revokeRenderedUrl();
    state.renderAbort = false;
    elements.renderButton.disabled = true;
    resetDownloadButton();

    const duration = selectedDuration();
    const quality = qualitySettings();
    const presetName = elements.preset.value;
    const basePreset = presets[presetName];
    const fps = Math.min(quality.fps, basePreset.fps);
    const ansiPercent = Number(elements.ansi.value);
    resizeCanvas(quality.width, quality.height);
    const randomizeTimeline = Boolean(elements.randomClip?.checked);
    const strength = elements.strength.value;
    const density = elements.density.value;
    const plan = chaos.buildPlan({
      sources: state.media,
      duration,
      randomize: randomizeTimeline,
      ansiPercent,
      projectSeed,
      presetName,
      preset: basePreset,
      strength,
      density,
      width: quality.width,
      height: quality.height,
      fps
    });
    const { timeline, ansiIntervals, resolvedPreset: preset, ansiGrid } = plan;
    state.lastPlanOracle = plan.oracle;
    const expectedFrames = Math.max(1, Math.ceil(duration * fps));
    const mimeType = pickRecorderMimeType();
    const chunks = [];
    const renderSession = {
      aborted: false,
      audioController: null,
      canvasStream: null,
      recorder: null,
      playback: null,
      abort() {
        this.aborted = true;
        this.audioController?.stop?.();
        void stopRenderPlayback(this.playback, true);
        if (this.recorder?.state && this.recorder.state !== 'inactive') {
          try { this.recorder.stop(); } catch { /* recorder already stopped */ }
        }
        this.canvasStream?.getTracks?.().forEach((track) => track.stop?.());
      }
    };
    state.activeRenderSession = renderSession;
    updateChaosUi();

    let canvasStream = null;
    let videoTracks = [];
    let mixedStream = null;
    let recorder = null;
    let manualCanvasFrames = false;
    let recorderStopped = false;
    let recorderStopFallback = false;
    let hardStop = 0;
    let startedAt = 0;
    let frameCount = 0;
    let audioDiagnostics = {};
    const renderPlayback = { segment: null, video: null, audioController: null };
    renderSession.playback = renderPlayback;

    try {
      await drawFrame(timeline, 0, duration, preset, ansiIntervals, ansiGrid, projectSeed, 0);
      canvasStream = elements.canvas.captureStream(0);
      renderSession.canvasStream = canvasStream;
      videoTracks = canvasStream.getVideoTracks();
      manualCanvasFrames = mimeType.includes('mp4') && typeof videoTracks[0]?.requestFrame === 'function';
      if (!manualCanvasFrames) {
        canvasStream.getTracks().forEach((track) => track.stop?.());
        canvasStream = elements.canvas.captureStream(fps);
        renderSession.canvasStream = canvasStream;
        videoTracks = canvasStream.getVideoTracks();
      }
      const requestCanvasFrame = () => {
        if (manualCanvasFrames) videoTracks[0]?.requestFrame?.();
      };
      requestCanvasFrame();
      mixedStream = new MediaStream(videoTracks);
      state.lastAudioMode = 'none';
      const audioController = await prepareAudioStream(duration, timeline, { includeSourceAudio, audioRequest });
      renderSession.audioController = audioController;
      renderPlayback.audioController = audioController;
      if (audioController?.track) mixedStream.addTrack(audioController.track);
      await audioController?.prepare?.();

      recorder = new MediaRecorder(mixedStream, mimeType ? { mimeType } : undefined);
      renderSession.recorder = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size) chunks.push(event.data);
      };
      const stopped = new Promise((resolve) => {
        recorder.onstop = () => {
          recorderStopped = true;
          resolve();
        };
      });
      const stopRecorder = () => {
        if (recorder.state !== 'inactive') {
          try { recorder.stop(); } catch { /* recorder already stopped */ }
        }
      };
      const finishRecorder = async () => {
        stopRecorder();
        const observed = await Promise.race([
          stopped.then(() => true),
          sleep(2000).then(() => false)
        ]);
        if (observed) return;
        recorderStopFallback = true;
        canvasStream?.getTracks?.().forEach((track) => track.stop?.());
        await Promise.race([stopped, sleep(750)]);
      };

      log(t('lite.log_render_armed', {
        seconds: duration.toFixed(1).replace('.0', ''),
        strength: strength.toUpperCase(),
        ansi: ansiPercent,
        density: density.toUpperCase(),
        width: quality.width,
        height: quality.height,
        fps
      }));
      log(t(randomizeTimeline ? 'lite.log_random_enabled' : 'lite.log_random_disabled'));
      log(t('lite.log_timeline', { segments: timeline.length, intervals: ansiIntervals.length, seed: chaos.seedLabel(projectSeed) }));
      log(t('lite.log_source_audio_state', { state: includeSourceAudio ? 'ON' : 'OFF', mode: state.lastAudioMode }));
      log(mimeType.includes('mp4') ? t('lite.log_mp4') : t('lite.log_webm'));
      setStatus(t('lite.status_rendering', { seconds: duration }));
      setProgress(0);
      startedAt = performance.now();
      const deadline = startedAt + duration * 1000;
      hardStop = window.setTimeout(stopRecorder, duration * 1000);
      recorder.start(250);
      requestCanvasFrame();
      await audioController?.start();

      while (!state.renderAbort && !renderSession.aborted && !recorderStopped) {
        const now = performance.now();
        if (now >= deadline) break;
        const elapsed = Math.max(0, Math.min(duration, (now - startedAt) / 1000));
        await drawFrame(timeline, elapsed, duration, preset, ansiIntervals, ansiGrid, projectSeed, frameCount, renderPlayback);
        requestCanvasFrame();
        frameCount += 1;
        setProgress((elapsed / duration) * 100);
        const nextFrameAt = startedAt + frameCount * (1000 / fps);
        const wait = Math.min(1000 / fps, Math.max(0, nextFrameAt - performance.now()));
        if (wait > 1) await sleep(wait);
      }

      window.clearTimeout(hardStop);
      await finishRecorder();
      await stopRenderPlayback(renderPlayback);
      audioDiagnostics = audioController?.diagnostics?.() || {};
      audioController?.stop();
      canvasStream.getTracks().forEach((track) => track.stop?.());

      if (renderSession.aborted || state.renderAbort) return;

      setProgress(100);
      const type = recorder.mimeType || mimeType || 'video/webm';
      const blob = new Blob(chunks, { type });
      if (!blob.size) throw new Error(t('lite.log_empty_recorder_output'));
      const renderMs = Math.max(1, performance.now() - startedAt);
      const effectiveFps = frameCount / (renderMs / 1000);
      state.renderedType = type;
      state.renderedBlob = blob;
      state.renderedUrl = URL.createObjectURL(blob);
      const extension = type.includes('mp4') ? 'mp4' : 'webm';
      state.renderedFilename = `wzrdvid-lite-${duration}s-${Date.now()}.${extension}`;
      const timelineMap = timeline.map((item) => ({
        sourceName: item.source.file.name,
        sourceKind: item.source.kind,
        outputStart: Number(item.start.toFixed(3)),
        outputEnd: Number((item.start + item.duration).toFixed(3)),
        sourceStart: Number(item.sourceStart.toFixed(3)),
        sourceEnd: Number((item.sourceStart + item.duration).toFixed(3))
      }));
      state.lastExportDiagnostics = {
        mimeType,
        recorderMimeType: recorder.mimeType || '',
        blobType: blob.type || '',
        blobSize: blob.size,
        filename: state.renderedFilename,
        videoTracks: videoTracks.length,
        videoTrackReadyState: videoTracks[0]?.readyState || '',
        canvasFrameMode: manualCanvasFrames ? 'manual' : 'interval',
        recorderStopFallback,
        audioTracks: mixedStream.getAudioTracks().length,
        mixedOutputAudioTracks: mixedStream.getAudioTracks().length,
        audioMode: state.lastAudioMode,
        includeSourceAudio,
        addedAudio: Boolean(state.audio),
        selectedDuration: Number(elements.duration?.value || DEFAULT_DURATION),
        renderDuration: duration,
        targetFps: fps,
        frames: frameCount,
        expectedFrames,
        effectiveFps: Number(effectiveFps.toFixed(2)),
        timelineSegments: timeline.length,
        timelineSources: new Set(timeline.map((item) => item.source.file.name)).size,
        timelineSourceNames: Array.from(new Set(timeline.map((item) => item.source.file.name))),
        timelineMap,
        projectSeed,
        chaosSeedLabel: chaos.seedLabel(projectSeed),
        effectStrength: strength,
        ansiDensity: density,
        ansiGrid,
        ...audioDiagnostics,
        audioRuntime: audioRuntimeDiagnostics()
      };
      elements.downloadButton.href = state.renderedUrl;
      elements.downloadButton.download = state.renderedFilename;
      elements.downloadButton.textContent = t('lite.download_type', { type: extension.toUpperCase() });
      elements.downloadButton.className = 'btn btn-primary';
      elements.downloadButton.removeAttribute('aria-disabled');
      setStatus(t('lite.status_complete', { seconds: duration, type: extension.toUpperCase() }));
      log(t('lite.log_render_complete', {
        seconds: duration,
        frames: frameCount,
        expected: expectedFrames,
        size: (blob.size / 1024 / 1024).toFixed(2),
        type: extension
      }));
    } catch (error) {
      if (!renderSession.aborted && !state.renderAbort) {
        log(t('lite.log_render_failed', { error: error?.message || String(error) }));
        setStatus(t('lite.status_render_failed'));
      }
    } finally {
      window.clearTimeout(hardStop);
      await stopRenderPlayback(renderPlayback, true);
      renderSession.audioController?.stop?.();
      if (recorder?.state && recorder.state !== 'inactive') {
        try { recorder.stop(); } catch { /* recorder already stopped */ }
      }
      canvasStream?.getTracks?.().forEach((track) => track.stop?.());
      if (state.activeRenderSession === renderSession) state.activeRenderSession = null;
      state.renderAbort = false;
      elements.renderButton.disabled = false;
      updateChaosUi();
    }
  }

  async function prepareAudioStream(duration, timeline, options) {
    const sourceVideos = Array.from(new Set(
      timeline.filter((item) => item.source.kind === 'video').map((item) => item.source.element)
    ));
    const sourceRequested = Boolean(options.includeSourceAudio && sourceVideos.length);
    if (sourceRequested) {
      const ready = await options.audioRequest.ready;
      if (ready && options.audioRequest.context) {
        const addedAudioBuffer = state.audio ? await decodeAddedAudio(options.audioRequest.context) : null;
        const controller = prepareSharedWebAudioController(duration, sourceVideos, options.audioRequest.context, true, addedAudioBuffer);
        if (controller) return controller;
      }
      log(t('lite.log_source_audio_unavailable'));
    }

    if (!state.audio) return null;
    const audio = state.audio.audio;
    const captureStream = audio.captureStream || audio.mozCaptureStream;
    if (captureStream) {
      audio.pause();
      audio.currentTime = 0;
      audio.loop = true;
      audio.volume = 0.92;
      audio.muted = false;
      audio.playsInline = true;
      const stream = captureStream.call(audio);
      const track = stream.getAudioTracks()[0];
      if (!track) {
        state.lastAudioMode = 'no-track';
        log(t('lite.log_no_audio_track'));
        return null;
      }
      state.lastAudioMode = 'captureStream';
      return makeAudioController({
        track,
        setLevel: (level) => { audio.volume = Math.max(0.0001, 0.92 * level); },
        startPlayback: async () => {
          audio.currentTime = 0;
          await audio.play().catch(() => log(t('lite.log_audio_blocked')));
        },
        stopPlayback: () => {
          audio.pause();
          audio.volume = 0.92;
        }
      }, duration, { sourceAudioReady: false, sourceNodesCreated: 0, sourceSwitchCount: 0 });
    }

    const request = options.audioRequest.context ? options.audioRequest : requestSharedAudioContext();
    const ready = await request.ready;
    const webAudioController = ready && request.context
      ? prepareSharedWebAudioController(duration, [], request.context, false, null)
      : null;
    if (webAudioController) return webAudioController;

    state.lastAudioMode = 'unavailable';
    log(t('lite.log_audio_capture_missing'));
    return null;
  }

  async function decodeAddedAudio(audioContext) {
    if (!state.audio) return null;
    if (state.audio.decodedContext === audioContext && state.audio.decodedBuffer) return state.audio.decodedBuffer;
    if (state.audio.decodedContext === audioContext && state.audio.decodePromise) return state.audio.decodePromise;
    const audioState = state.audio;
    audioState.decodedContext = audioContext;
    audioState.decodePromise = audioState.file.arrayBuffer()
      .then((bytes) => audioContext.decodeAudioData(bytes.slice(0)))
      .then((buffer) => {
        if (state.audio === audioState) audioState.decodedBuffer = buffer;
        return buffer;
      })
      .catch(() => null);
    return audioState.decodePromise;
  }

  function prepareSharedWebAudioController(duration, sourceVideos, audioContext, sourceAudioRequested, addedAudioBuffer) {
    if (!audioContext.createMediaElementSource || !audioContext.createMediaStreamDestination) return null;

    const connections = [];
    const sourceEntries = new Map();
    let sourceVideoNodesCreated = 0;
    let addedAudioNodeCreated = false;
    let sourceSwitchCount = 0;
    let activeSource = null;
    let stopped = false;
    let fadeTimer = 0;
    let fadeInterval = 0;
    let addedLoopInterval = 0;
    let destination;
    let master;
    let sourceBus;
    let addedBus;
    let addedElement = null;
    let addedGain = null;
    let addedBufferSource = null;
    let restartAddedAudio = null;

    const connect = (from, to) => {
      from.connect(to);
      audioRuntime.activeConnections += 1;
      connections.push(() => {
        try { from.disconnect(to); } catch { /* already disconnected */ }
        audioRuntime.activeConnections = Math.max(0, audioRuntime.activeConnections - 1);
      });
    };

    try {
      destination = audioContext.createMediaStreamDestination();
      master = audioContext.createGain();
      master.gain.value = 1;
      connect(master, destination);
      connect(master, audioContext.destination);

      if (sourceAudioRequested) {
        sourceBus = audioContext.createGain();
        sourceBus.gain.value = 1;
        connect(sourceBus, master);
        for (const video of sourceVideos) {
          const cached = cachedMediaElementSource(audioContext, video);
          if (cached.created) sourceVideoNodesCreated += 1;
          const gain = audioContext.createGain();
          gain.gain.value = 0;
          connect(cached.node, gain);
          connect(gain, sourceBus);
          sourceEntries.set(video, { gain });
          video.muted = false;
          video.playsInline = true;
        }
      }

      if (state.audio) {
        addedGain = audioContext.createGain();
        addedGain.gain.value = 0;
        addedBus = audioContext.createGain();
        addedBus.gain.value = 1;
        if (!addedAudioBuffer) {
          addedElement = new Audio(state.audio.url);
          addedElement.preload = 'auto';
          addedElement.loop = false;
          addedElement.volume = 1;
          addedElement.muted = false;
          addedElement.playsInline = true;
          state.audio.mixElement = addedElement;
          const cached = cachedMediaElementSource(audioContext, addedElement);
          addedAudioNodeCreated = cached.created;
          connect(cached.node, addedGain);
        }
        connect(addedGain, addedBus);
        connect(addedBus, master);
      }
    } catch {
      while (connections.length) connections.pop()();
      sourceVideos.forEach((video) => { video.muted = true; });
      return null;
    }

    const track = destination.stream.getAudioTracks()[0];
    if (!track) {
      while (connections.length) connections.pop()();
      sourceVideos.forEach((video) => { video.muted = true; });
      log(t('lite.log_no_audio_track'));
      return null;
    }

    if (sourceAudioRequested && state.audio) state.lastAudioMode = 'mixedWebAudio';
    else if (sourceAudioRequested) state.lastAudioMode = 'sourceWebAudio';
    else state.lastAudioMode = 'webAudio';
    audioRuntime.activeControllers += 1;

    const rampGain = (entry, target, immediate = false) => {
      const now = audioContext.currentTime;
      const param = entry.gain.gain;
      param.cancelScheduledValues(now);
      param.setValueAtTime(param.value, now);
      if (immediate) param.setValueAtTime(target, now);
      else param.linearRampToValueAtTime(target, now + SOURCE_AUDIO_RAMP_SECONDS);
    };

    return {
      track,
      prepare: async () => {
        await Promise.all(sourceVideos.map((video) => waitForPlayable(video, 600)));
        if (addedElement) await waitForPlayable(addedElement, 1500, true);
        const mediaToPrime = [...sourceVideos, ...(addedElement ? [addedElement] : [])];
        for (const media of mediaToPrime) {
          const originalTime = Number(media.currentTime || 0);
          await media.play().catch(() => {});
          await sleep(80);
          media.pause();
          await seekVideo(media, originalTime);
        }
        await sleep(SOURCE_AUDIO_RAMP_SECONDS * 1000);
      },
      hasSource: (video) => sourceEntries.has(video),
      activateSource: (video) => {
        const next = sourceEntries.get(video);
        if (!next || activeSource === video) return;
        if (activeSource) rampGain(sourceEntries.get(activeSource), 0);
        activeSource = video;
        rampGain(next, 1);
        sourceSwitchCount += 1;
      },
      deactivateSource: async (video, immediate = false) => {
        if (!video || activeSource !== video) return;
        rampGain(sourceEntries.get(video), 0, immediate);
        activeSource = null;
        if (!immediate) await sleep(SOURCE_AUDIO_RAMP_SECONDS * 1000);
      },
      start: async () => {
        if (audioContext.state === 'suspended') await audioContext.resume().catch(() => {});
        if (addedAudioBuffer) {
          addedBufferSource = audioContext.createBufferSource();
          addedBufferSource.buffer = addedAudioBuffer;
          addedBufferSource.loop = true;
          connect(addedBufferSource, addedGain);
          addedGain.gain.value = 0.92;
          addedBufferSource.start();
        }
        if (addedElement) {
          await seekVideo(addedElement, 0);
          addedGain.gain.value = 0.92;
          restartAddedAudio = () => {
            if (stopped) return;
            addedElement.currentTime = 0;
            void addedElement.play().catch(() => log(t('lite.log_audio_blocked')));
          };
          addedElement.addEventListener('ended', restartAddedAudio);
          await addedElement.play().catch(() => log(t('lite.log_audio_blocked')));
          addedLoopInterval = window.setInterval(() => {
            const remaining = Number(addedElement.duration || 0) - Number(addedElement.currentTime || 0);
            if (addedElement.ended || (Number.isFinite(remaining) && remaining >= 0 && remaining < 0.12)) restartAddedAudio();
          }, 60);
        }
        if (!addedGain) return;
        fadeTimer = window.setTimeout(() => {
          const started = performance.now();
          fadeInterval = window.setInterval(() => {
            const progress = Math.min(1, (performance.now() - started) / 1800);
            addedGain.gain.value = Math.max(0.0001, 0.92 * (1 - progress));
            if (progress >= 1) window.clearInterval(fadeInterval);
          }, 80);
        }, Math.max(0, duration - 2.0) * 1000);
      },
      diagnostics: () => ({
        sourceAudioRequested,
        sourceAudioReady: sourceAudioRequested && sourceEntries.size > 0,
        sourceBusReady: Boolean(sourceBus),
        sourceNodesInGraph: sourceEntries.size,
        sourceNodesCreated: sourceVideoNodesCreated,
        addedAudioNodeCreated,
        addedAudioBufferReady: Boolean(addedAudioBuffer),
        sourceSwitchCount,
        addedAudioCurrentTime: Number(addedElement?.currentTime || 0),
        addedAudioDuration: Number(addedElement?.duration || 0),
        sharedAudioContextCount: audioRuntime.contextCount,
        sharedAudioContextState: audioContext.state,
        mixedOutputAudioTracks: destination.stream.getAudioTracks().length
      }),
      stop: () => {
        if (stopped) return;
        stopped = true;
        window.clearTimeout(fadeTimer);
        window.clearInterval(fadeInterval);
        window.clearInterval(addedLoopInterval);
        sourceEntries.forEach((entry, video) => {
          rampGain(entry, 0, true);
          try { video.pause(); } catch { /* video already stopped */ }
          video.muted = true;
        });
        if (addedElement) {
          if (restartAddedAudio) addedElement.removeEventListener('ended', restartAddedAudio);
          addedElement.pause();
          addedGain.gain.value = 0;
          releaseMediaElementSource(addedElement);
          if (state.audio?.mixElement === addedElement) state.audio.mixElement = null;
        }
        if (addedBufferSource) {
          try { addedBufferSource.stop(); } catch { /* buffer source may already be stopped */ }
        }
        track.stop();
        while (connections.length) connections.pop()();
        audioRuntime.activeControllers = Math.max(0, audioRuntime.activeControllers - 1);
      }
    };
  }

  function makeAudioController(playback, duration, diagnostics = {}) {
    let fadeTimer = 0;
    let fadeInterval = 0;
    let stopped = false;
    audioRuntime.activeControllers += 1;
    return {
      track: playback.track,
      prepare: async () => {},
      hasSource: () => false,
      activateSource: () => {},
      deactivateSource: async () => {},
      start: async () => {
        await playback.startPlayback();
        fadeTimer = window.setTimeout(() => {
          const started = performance.now();
          fadeInterval = window.setInterval(() => {
            const progress = Math.min(1, (performance.now() - started) / 1800);
            playback.setLevel(1 - progress);
            if (progress >= 1) window.clearInterval(fadeInterval);
          }, 80);
        }, Math.max(0, duration - 2.0) * 1000);
      },
      diagnostics: () => ({
        sourceAudioRequested: false,
        sourceAudioReady: false,
        sourceBusReady: false,
        sourceNodesInGraph: 0,
        mixedOutputAudioTracks: playback.track ? 1 : 0,
        ...diagnostics
      }),
      stop: () => {
        if (stopped) return;
        stopped = true;
        window.clearTimeout(fadeTimer);
        window.clearInterval(fadeInterval);
        playback.stopPlayback();
        playback.track?.stop?.();
        audioRuntime.activeControllers = Math.max(0, audioRuntime.activeControllers - 1);
      }
    };
  }

  async function drawFrame(timeline, time, duration, preset, ansiIntervals, ansiGrid, projectSeed, frameIndex, playback = null) {
    const segment = timeline.find((item) => time >= item.start && time < item.start + item.duration) || timeline[timeline.length - 1];
    const localTime = Math.max(0, time - segment.start);
    if (segment.source.kind === 'video') {
      if (playback) {
        await preparePlaybackVideo(playback, segment, localTime, timeline);
      } else {
        await seekVideo(segment.source.element, segment.sourceStart + localTime);
      }
    } else if (playback?.video) {
      await stopRenderPlayback(playback);
    }
    if (playback) scheduleUpcomingPlayback(playback, segment, timeline);
    drawSource(segment, localTime, time, duration, preset);
    if (isAnsiTime(time, ansiIntervals)) drawAnsi(preset, time, ansiGrid);
    applyPresetEffects(preset, time, duration, chaos.frameChaos(projectSeed, frameIndex));
  }

  function scheduleUpcomingPlayback(playback, segment, timeline) {
    if (!playback.preparedSegments) playback.preparedSegments = new Map();
    const index = timeline.indexOf(segment);
    const next = timeline[index + 1];
    if (!next || next.source.kind !== 'video' || next.source.element === segment.source.element || playback.preparedSegments.has(next)) return;
    const video = next.source.element;
    const preparation = (async () => {
      video.muted = !playback.audioController?.hasSource?.(video);
      video.playsInline = true;
      video.pause();
      await seekVideo(video, next.sourceStart);
      await waitForPlayable(video, 600);
      await waitForVideoFrame(video);
    })();
    playback.preparedSegments.set(next, preparation);
  }

  async function preparePlaybackVideo(playback, segment, localTime, timeline) {
    const video = segment.source.element;
    const expected = segment.sourceStart + localTime;
    if (playback.segment !== segment || playback.video !== video) {
      await stopRenderPlayback(playback);
      playback.segment = segment;
      playback.video = video;
      video.muted = !playback.audioController?.hasSource?.(video);
      video.playsInline = true;
      video.loop = false;
      const prepared = playback.preparedSegments?.get(segment);
      if (prepared) await prepared;
      else {
        await seekVideo(video, segment.sourceStart);
        await waitForPlayable(video, 600);
      }
      await video.play().catch(() => {});
      playback.audioController?.activateSource?.(video);
      await waitForVideoFrame(video);
      scheduleUpcomingPlayback(playback, segment, timeline);
      return;
    }
    if (video.paused) await video.play().catch(() => {});
    if (Math.abs((video.currentTime || 0) - expected) > 1.0) {
      await playback.audioController?.deactivateSource?.(video);
      video.pause();
      await seekVideo(video, expected);
      await waitForPlayable(video, 600);
      await video.play().catch(() => {});
      playback.audioController?.activateSource?.(video);
      await waitForVideoFrame(video);
    }
  }

  async function stopRenderPlayback(playback, immediate = false) {
    if (!playback?.video) return;
    const video = playback.video;
    await playback.audioController?.deactivateSource?.(video, immediate);
    try { video.pause(); } catch { /* video already stopped */ }
    video.muted = true;
    playback.segment = null;
    playback.video = null;
  }

  function drawSource(segment, localTime, time, duration, preset) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const source = segment.source.element;
    const maxZoom = 0.18 + preset.punch * 0.48;
    const tunnel = (time % 4.5) / 4.5;
    const beat = state.audio ? Math.pow(Math.max(0, Math.sin(time * Math.PI * 2 * 1.35 + segment.seed * 9)), 8) : 0;
    const punch = (Math.sin(time * 6.2 + segment.seed * 12) > 0.955) ? 0.22 : 0;
    const zoom = 1 + tunnel * maxZoom + punch + beat * (0.03 + preset.punch * 0.08);
    const wobbleX = Math.sin(time * 7.1 + segment.seed * 6) * preset.tape * 10 + beat * preset.rgb * 1.2;
    const wobbleY = Math.cos(time * 5.7 + segment.seed * 8) * preset.tape * 5;
    ctx.save();
    ctx.fillStyle = '#080706';
    ctx.fillRect(0, 0, w, h);
    ctx.translate(w / 2 + wobbleX, h / 2 + wobbleY);
    ctx.scale(zoom, zoom);
    ctx.translate(-w / 2, -h / 2);
    drawCover(source, w, h);
    ctx.restore();
    if (duration - time < 0.7) {
      ctx.fillStyle = `rgba(8, 7, 6, ${1 - Math.max(0, duration - time) / 0.7})`;
      ctx.fillRect(0, 0, w, h);
    }
    if (preset.profile === 'publicAccess') applyPublicAccessSource(preset, time);
  }

  function drawCover(source, w, h) {
    const sourceWidth = source.videoWidth || source.naturalWidth || w;
    const sourceHeight = source.videoHeight || source.naturalHeight || h;
    const scale = Math.max(w / sourceWidth, h / sourceHeight);
    const drawWidth = sourceWidth * scale;
    const drawHeight = sourceHeight * scale;
    const x = (w - drawWidth) / 2;
    const y = (h - drawHeight) / 2;
    try {
      ctx.drawImage(source, x, y, drawWidth, drawHeight);
    } catch {
      drawFallbackSignal(w, h);
    }
  }

  function drawFallbackSignal(w, h) {
    const gradient = ctx.createLinearGradient(0, 0, w, h);
    gradient.addColorStop(0, '#20142a');
    gradient.addColorStop(0.5, '#0c1417');
    gradient.addColorStop(1, '#2c1833');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 0.18;
    ctx.fillStyle = '#a9f4cb';
    for (let y = 0; y < h; y += 12) {
      ctx.fillRect(0, y, w, 1);
    }
    ctx.globalAlpha = 1;
  }

  function drawAnsi(preset, time, grid) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const cols = grid.columns;
    const rows = grid.rows;
    ansiCanvas.width = cols;
    ansiCanvas.height = rows;
    ansiCtx.imageSmoothingEnabled = false;
    ansiCtx.drawImage(elements.canvas, 0, 0, cols, rows);
    const pixels = ansiCtx.getImageData(0, 0, cols, rows).data;
    ctx.fillStyle = '#080706';
    ctx.fillRect(0, 0, w, h);
    const cellW = w / cols;
    const cellH = h / rows;
    ctx.font = `900 ${Math.ceil(cellH * 1.18)}px ui-monospace, Menlo, Consolas, monospace`;
    ctx.textBaseline = 'middle';
    const ramp = preset.ramp;
    for (let y = 0; y < rows; y += 1) {
      for (let x = 0; x < cols; x += 1) {
        const index = (y * cols + x) * 4;
        let r = pixels[index];
        let g = pixels[index + 1];
        let b = pixels[index + 2];
        const brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255;
        const char = ramp[Math.min(ramp.length - 1, Math.floor(brightness * ramp.length))];
        if (char === ' ') continue;
        const drift = Math.sin(time * 1.5 + x * 0.11 + y * 0.08) * 14;
        r = Math.max(0, Math.min(255, r + drift));
        b = Math.max(0, Math.min(255, b - drift));
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillText(char, x * cellW, y * cellH + cellH * 0.52);
      }
    }
  }

  function applyPresetEffects(preset, time, duration, frameDecisions) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    if (preset.rgb > 0 && Math.sin(time * 11.7) > 0.72) {
      ctx.globalCompositeOperation = 'screen';
      ctx.globalAlpha = 0.22;
      ctx.drawImage(elements.canvas, preset.rgb, 0);
      ctx.drawImage(elements.canvas, -preset.rgb, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }
    if (preset.mosaic > 0 && (Math.sin(time * 2.4) > 0.92 || duration - time < 1.1)) {
      const scale = Math.max(0.08, 0.2 - preset.mosaic * 0.08);
      const sw = Math.max(24, Math.floor(w * scale));
      const sh = Math.max(14, Math.floor(h * scale));
      tempCanvas.width = sw;
      tempCanvas.height = sh;
      tempCtx.imageSmoothingEnabled = false;
      tempCtx.drawImage(elements.canvas, 0, 0, sw, sh);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tempCanvas, 0, 0, sw, sh, 0, 0, w, h);
      ctx.imageSmoothingEnabled = true;
    }
    drawTapeDamage(preset.tape, time, frameDecisions.tape);
    if (preset.profile === 'publicAccess') drawPublicAccessOverlay(preset, time, frameDecisions.publicAccess);
    drawScanlines(preset.scanlines);
  }

  function applyPublicAccessSource(preset, time) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const frame = ctx.getImageData(0, 0, w, h);
    const data = frame.data;
    const drift = Math.sin(time * 0.77) * 8;
    for (let index = 0; index < data.length; index += 4) {
      const r = data[index];
      const g = data[index + 1];
      const b = data[index + 2];
      const luma = r * 0.299 + g * 0.587 + b * 0.114;
      data[index] = clampByte(r * 0.72 + luma * 0.24 + 18 + drift);
      data[index + 1] = clampByte(g * 0.68 + luma * 0.25 + 12);
      data[index + 2] = clampByte(b * 0.62 + luma * 0.28 - 12 - drift);
    }
    ctx.putImageData(frame, 0, 0);

    ctx.globalAlpha = 0.16;
    ctx.globalCompositeOperation = 'screen';
    ctx.drawImage(elements.canvas, Math.max(1, preset.rgb), 0);
    ctx.globalCompositeOperation = 'multiply';
    ctx.drawImage(elements.canvas, -Math.max(1, preset.rgb - 1), 0);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';

    ctx.fillStyle = `rgba(246, 235, 212, ${0.045 + 0.018 * Math.sin(time * 1.9)})`;
    ctx.fillRect(0, 0, w, h);
  }

  function drawPublicAccessOverlay(preset, time, decisions) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const bandHeight = Math.max(12, Math.floor(h * 0.065));
    const bandY = h - bandHeight + Math.floor(Math.sin(time * 5.5) * 4);
    ctx.save();
    ctx.globalAlpha = 0.62;
    for (let y = 0; y < bandHeight; y += 3) {
      const offset = Math.sin(time * 13 + y * 0.7) * 24 * preset.tape;
      tempCanvas.width = w;
      tempCanvas.height = 2;
      tempCtx.drawImage(elements.canvas, 0, Math.max(0, bandY + y), w, 2, 0, 0, w, 2);
      ctx.drawImage(tempCanvas, offset, Math.max(0, bandY + y));
    }
    ctx.fillStyle = 'rgba(0, 0, 0, 0.18)';
    ctx.fillRect(0, Math.max(0, bandY), w, bandHeight);
    ctx.fillStyle = 'rgba(169, 244, 203, 0.08)';
    ctx.fillRect(0, Math.max(0, bandY + 2), w, 2);
    ctx.fillStyle = 'rgba(244, 166, 207, 0.08)';
    ctx.fillRect(0, Math.max(0, bandY + bandHeight - 4), w, 2);

    const dropoutCount = Math.floor(2 + preset.tape * 6);
    for (let i = 0; i < dropoutCount; i += 1) {
      const decision = decisions[i];
      const y = Math.floor(decision.y * h);
      const x = Math.floor(decision.x * w * 0.82);
      const width = Math.floor(w * 0.08 + decision.width * w * 0.37);
      ctx.fillStyle = decision.light > 0.55 ? 'rgba(255,255,235,0.15)' : 'rgba(0,0,0,0.18)';
      ctx.fillRect(x, y, width, Math.max(1, Math.floor(1 + decision.height * 3)));
    }
    ctx.restore();
  }

  function drawTapeDamage(amount, time, decisions) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const tears = Math.floor(amount * 7);
    for (let i = 0; i < tears; i += 1) {
      const decision = decisions[i];
      if (decision.gate > amount * 0.42) continue;
      const y = Math.floor(decision.y * h);
      const height = Math.floor(2 + decision.height * 13);
      const xOffset = Math.floor(Math.sin(time * 12 + i) * amount * 36);
      tempCanvas.width = w;
      tempCanvas.height = height;
      tempCtx.drawImage(elements.canvas, 0, y, w, height, 0, 0, w, height);
      ctx.drawImage(tempCanvas, 0, 0, w, height, xOffset, y, w, height);
      ctx.fillStyle = `rgba(255, 90, 168, ${0.08 + amount * 0.08})`;
      ctx.fillRect(0, y, w, 1);
    }
  }

  function drawScanlines(amount) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    ctx.fillStyle = `rgba(0, 0, 0, ${amount * 0.22})`;
    for (let y = 0; y < h; y += 4) ctx.fillRect(0, y, w, 1);
  }

  function clampByte(value) {
    return Math.max(0, Math.min(255, Math.round(value)));
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function setupDropZone(zone, callback) {
    ['dragenter', 'dragover'].forEach((name) => {
      zone.addEventListener(name, (event) => {
        event.preventDefault();
        zone.classList.add('dragging');
      });
    });
    ['dragleave', 'drop'].forEach((name) => {
      zone.addEventListener(name, () => zone.classList.remove('dragging'));
    });
    zone.addEventListener('drop', async (event) => {
      event.preventDefault();
      await callback(Array.from(event.dataTransfer.files || []));
    });
  }

  elements.mediaButton.addEventListener('click', () => elements.mediaInput.click());
  elements.audioButton.addEventListener('click', () => elements.audioInput.click());
  elements.mediaDrop.addEventListener('click', () => elements.mediaInput.click());
  elements.audioDrop.addEventListener('click', () => elements.audioInput.click());
  elements.mediaInput.addEventListener('change', async () => {
    const files = Array.from(elements.mediaInput.files || []);
    elements.mediaInput.value = '';
    await addMediaFiles(files);
  });
  elements.audioInput.addEventListener('change', async () => {
    const file = elements.audioInput.files?.[0];
    elements.audioInput.value = '';
    if (file) await setAudioFile(file);
  });
  elements.resetButton?.addEventListener('click', clearProject);
  elements.rerollChaos?.addEventListener('click', rerollChaos);
  setupDropZone(elements.mediaDrop, addMediaFiles);
  setupDropZone(elements.audioDrop, async (files) => {
    const file = files.find((candidate) => ['audio', 'video'].includes(fileKind(candidate)));
    if (file) await setAudioFile(file);
  });
  elements.ansi.addEventListener('input', () => {
    elements.ansiValue.textContent = `${elements.ansi.value}%`;
  });
  elements.duration.addEventListener('change', updateRenderButtonCopy);
  elements.quality.addEventListener('change', drawIdleFrame);
  elements.renderButton.addEventListener('click', renderClip);
  document.addEventListener('wzrdvid:i18n', updateLocalizedRuntimeText);

  window.addEventListener('beforeunload', () => {
    state.activeRenderSession?.abort?.();
    revokeRenderedUrl();
    state.media.forEach((item) => URL.revokeObjectURL(item.url));
    clearAddedAudio();
    audioRuntime.context?.close?.();
  });

  updateLocalizedRuntimeText();
  drawIdleFrame();
  log(t('lite.log_armed'));
})();
