(() => {
  'use strict';

  const DEFAULT_DURATION = 30;
  const MIN_ANSI_CHUNK = 0.5;
  const MAX_ANSI_CHUNK = 3.0;
  const VIDEO_EXTENSIONS = new Set(['mp4', 'mov', 'm4v', 'webm', 'mkv', 'avi']);
  const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp', 'gif']);
  const AUDIO_EXTENSIONS = new Set(['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'aif', 'aiff']);

  const presets = {
    'Chunkcore Chaos': { grid: 74, ramp: '  ░▒▓█', scanlines: 0.34, rgb: 5, tape: 0.34, mosaic: 0.4, punch: 0.28, fps: 15 },
    'Classic ANSI Lite': { grid: 96, ramp: ' .:-=+*#%@', scanlines: 0.2, rgb: 2, tape: 0.12, mosaic: 0.14, punch: 0.16, fps: 15 },
    'VHS Damage Lite': { grid: 84, ramp: '  ░▒▓█', scanlines: 0.46, rgb: 8, tape: 0.58, mosaic: 0.26, punch: 0.22, fps: 15 },
    'Dial-Up Glitch': { grid: 68, ramp: '  ░▒▓█', scanlines: 0.28, rgb: 9, tape: 0.44, mosaic: 0.62, punch: 0.36, fps: 15 },
    'Public Access': { grid: 88, ramp: ' .:-=+*#%@', scanlines: 0.18, rgb: 3, tape: 0.24, mosaic: 0.2, punch: 0.2, fps: 15 }
  };

  const state = {
    media: [],
    audio: null,
    renderedUrl: null,
    renderedType: '',
    renderAbort: false
  };

  const elements = {
    mediaDrop: document.getElementById('mediaDrop'),
    mediaInput: document.getElementById('mediaInput'),
    mediaButton: document.getElementById('mediaButton'),
    audioDrop: document.getElementById('audioDrop'),
    audioInput: document.getElementById('audioInput'),
    audioButton: document.getElementById('audioButton'),
    fileList: document.getElementById('fileList'),
    preset: document.getElementById('presetSelect'),
    ansi: document.getElementById('ansiAmount'),
    ansiValue: document.getElementById('ansiValue'),
    duration: document.getElementById('durationSelect'),
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

  function extensionOf(file) {
    return (file.name.split('.').pop() || '').toLowerCase();
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
    state.renderedType = '';
  }

  async function addMediaFiles(files) {
    const accepted = [];
    for (const file of files) {
      const kind = fileKind(file);
      if (kind === 'video' || kind === 'image') accepted.push({ file, kind });
      if (kind === 'audio') await setAudioFile(file);
    }
    if (!accepted.length) {
      log('No timeline media found in that drop.');
      return;
    }
    for (const item of accepted) {
      const prepared = await prepareTimelineItem(item.file, item.kind);
      state.media.push(prepared);
      log(`loaded ${item.kind}: ${item.file.name}`);
    }
    updateFileList();
    drawIdleFrame();
  }

  async function setAudioFile(file) {
    const kind = fileKind(file);
    if (kind !== 'audio' && kind !== 'video') {
      log(`ignored audio drop: ${file.name}`);
      return;
    }
    if (state.audio?.url) URL.revokeObjectURL(state.audio.url);
    const url = URL.createObjectURL(file);
    const audio = new Audio(url);
    audio.preload = 'metadata';
    state.audio = { file, url, audio };
    log(`audio armed: ${file.name}`);
    updateFileList();
  }

  async function prepareTimelineItem(file, kind) {
    const url = URL.createObjectURL(file);
    if (kind === 'video') {
      const video = document.createElement('video');
      video.src = url;
      video.muted = true;
      video.playsInline = true;
      video.preload = 'auto';
      await waitForMetadata(video).catch(() => undefined);
      return { file, kind, url, element: video, duration: Number.isFinite(video.duration) ? video.duration : 3 };
    }
    const image = new Image();
    image.decoding = 'async';
    image.src = url;
    await image.decode().catch(() => undefined);
    return { file, kind, url, element: image, duration: 2.4 };
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

  function updateFileList() {
    const lines = [];
    state.media.forEach((item, index) => {
      const duration = item.kind === 'video' ? `${(item.duration || 0).toFixed(1)}s` : '1-3s hold';
      lines.push(`<li>${index + 1}. ${escapeHtml(item.file.name)} <span>// ${item.kind} // ${duration}</span></li>`);
    });
    if (state.audio) lines.push(`<li>AUDIO. ${escapeHtml(state.audio.file.name)} <span>// local audio bus</span></li>`);
    elements.fileList.innerHTML = lines.join('') || '<li>No media loaded yet.</li>';
  }

  function escapeHtml(value) {
    return value.replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  }

  function selectedDuration() {
    const value = Number(elements.duration?.value || DEFAULT_DURATION);
    return [15, 30, 60].includes(value) ? value : DEFAULT_DURATION;
  }

  function updateRenderButtonCopy() {
    elements.renderButton.textContent = `MAKE ${selectedDuration()} SEC CLIP`;
  }

  function makeTimeline(duration) {
    const timeline = [];
    let t = 0;
    let guard = 0;
    while (t < duration - 0.001 && guard < 240) {
      guard += 1;
      const source = state.media[Math.floor(Math.random() * state.media.length)];
      const isVideo = source.kind === 'video';
      const segmentDuration = isVideo ? randomBetween(1.2, 4.2) : randomBetween(1, 3);
      const safeDuration = Math.min(segmentDuration, duration - t);
      if (safeDuration <= 0.001) break;
      const sourceMax = Math.max(0, (source.duration || safeDuration) - safeDuration);
      const sourceStart = isVideo ? Math.random() * sourceMax : 0;
      timeline.push({
        source,
        start: t,
        duration: safeDuration,
        sourceStart,
        seed: Math.random()
      });
      t += safeDuration;
    }
    if (timeline.length) {
      const last = timeline[timeline.length - 1];
      last.duration = Math.max(0, duration - last.start);
    }
    return timeline;
  }

  function buildAnsiIntervals(duration, percent, minLen = MIN_ANSI_CHUNK, maxLen = MAX_ANSI_CHUNK, seed = Date.now()) {
    const clampedPercent = Math.max(0, Math.min(100, Number(percent) || 0));
    if (duration <= 0 || clampedPercent <= 0) return [];
    if (clampedPercent >= 100) return [[0, duration]];

    const rng = seededRandom(seed);
    const chunks = [];
    let t = 0;
    while (t < duration - 0.001) {
      const remaining = duration - t;
      const len = Math.min(remaining, randomBetween(minLen, maxLen, rng));
      chunks.push([t, t + len]);
      t += len;
    }

    shuffle(chunks, rng);
    const target = duration * clampedPercent / 100;
    const selected = [];
    let selectedTotal = 0;
    for (const [start, end] of chunks) {
      if (selectedTotal >= target - 0.05) break;
      const available = end - start;
      const remaining = target - selectedTotal;
      if (available > remaining && remaining >= minLen) {
        selected.push([start, Math.min(end, start + remaining)]);
        selectedTotal += remaining;
      } else if (available <= remaining || remaining > available * 0.5) {
        selected.push([start, end]);
        selectedTotal += available;
      }
    }
    return mergeIntervals(selected, duration);
  }

  function isAnsiTime(time, intervals) {
    return intervals.some(([start, end]) => time >= start && time < end);
  }

  function mergeIntervals(intervals, duration) {
    const sorted = intervals
      .map(([start, end]) => [Math.max(0, start), Math.min(duration, end)])
      .filter(([start, end]) => end - start > 0.01)
      .sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const interval of sorted) {
      const last = merged[merged.length - 1];
      if (last && interval[0] <= last[1] + 0.001) {
        last[1] = Math.max(last[1], interval[1]);
      } else {
        merged.push(interval);
      }
    }
    return merged;
  }

  function seededRandom(seed) {
    let value = seed >>> 0;
    return () => {
      value += 0x6D2B79F5;
      let next = value;
      next = Math.imul(next ^ (next >>> 15), next | 1);
      next ^= next + Math.imul(next ^ (next >>> 7), next | 61);
      return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffle(items, rng) {
    for (let i = items.length - 1; i > 0; i -= 1) {
      const j = Math.floor(rng() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
  }

  function randomBetween(min, max, rng = Math.random) {
    return min + rng() * (max - min);
  }

  function qualitySettings() {
    if (elements.quality.value === 'better') return { width: 1280, height: 720, fps: 18 };
    return { width: 854, height: 480, fps: 15 };
  }

  function drawIdleFrame() {
    const { width, height } = qualitySettings();
    resizeCanvas(width, height);
    ctx.fillStyle = '#080706';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#a9f4cb';
    ctx.font = `900 ${Math.max(24, width / 28)}px ui-monospace, monospace`;
    ctx.fillText('//wzrdVID Lite', width * 0.06, height * 0.42);
    ctx.fillStyle = '#f4a6cf';
    ctx.font = `800 ${Math.max(14, width / 54)}px ui-monospace, monospace`;
    ctx.fillText('local browser render // no upload', width * 0.06, height * 0.52);
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
      log('add at least one video or image before rendering');
      return;
    }
    if (!window.MediaRecorder || !elements.canvas.captureStream) {
      log('MediaRecorder or canvas capture is not available in this browser.');
      return;
    }

    revokeRenderedUrl();
    state.renderAbort = false;
    elements.renderButton.disabled = true;
    elements.downloadButton.className = 'btn btn-disabled';
    elements.downloadButton.removeAttribute('href');
    elements.downloadButton.setAttribute('aria-disabled', 'true');

    const duration = selectedDuration();
    const quality = qualitySettings();
    const preset = presets[elements.preset.value];
    const fps = Math.min(quality.fps, preset.fps);
    const ansiPercent = Number(elements.ansi.value);
    const ansiSeed = window.crypto?.getRandomValues ? window.crypto.getRandomValues(new Uint32Array(1))[0] : Math.floor(Math.random() * 2 ** 32);
    resizeCanvas(quality.width, quality.height);
    const timeline = makeTimeline(duration);
    const ansiIntervals = buildAnsiIntervals(duration, ansiPercent, MIN_ANSI_CHUNK, MAX_ANSI_CHUNK, ansiSeed);
    const expectedFrames = Math.max(1, Math.ceil(duration * fps));
    const mimeType = pickRecorderMimeType();
    const chunks = [];
    const canvasStream = elements.canvas.captureStream(fps);
    const mixedStream = new MediaStream(canvasStream.getVideoTracks());
    const audioController = await prepareAudioStream(duration);
    if (audioController?.track) mixedStream.addTrack(audioController.track);

    const recorder = new MediaRecorder(mixedStream, mimeType ? { mimeType } : undefined);
    let recorderStopped = false;
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

    log(`render armed: ${duration.toFixed(0)} sec // ANSI coverage ${ansiPercent}% // ${quality.width}x${quality.height} // ${fps} fps`);
    log(`timeline segments: ${timeline.length} // ANSI intervals: ${ansiIntervals.length} // seed ${ansiSeed}`);
    log(mimeType.includes('mp4') ? 'browser MP4 recorder available' : 'browser MP4 recorder unavailable; using WebM prototype fallback');
    setStatus(`rendering ${duration} sec local clip // no upload`);
    setProgress(0);
    const startedAt = performance.now();
    const deadline = startedAt + duration * 1000;
    const hardStop = window.setTimeout(stopRecorder, duration * 1000);
    let frameCount = 0;
    recorder.start(250);
    await audioController?.start();

    while (!state.renderAbort && !recorderStopped) {
      const now = performance.now();
      if (now >= deadline) break;
      const elapsed = Math.max(0, Math.min(duration, (now - startedAt) / 1000));
      await drawFrame(timeline, elapsed, duration, preset, ansiIntervals);
      frameCount += 1;
      setProgress((elapsed / duration) * 100);
      const nextFrameAt = startedAt + frameCount * (1000 / fps);
      const wait = Math.min(1000 / fps, Math.max(0, nextFrameAt - performance.now()));
      if (wait > 1) await sleep(wait);
    }

    window.clearTimeout(hardStop);
    audioController?.stop();
    stopRecorder();
    await stopped;
    setProgress(100);
    elements.renderButton.disabled = false;

    const type = recorder.mimeType || mimeType || 'video/webm';
    const blob = new Blob(chunks, { type });
    state.renderedType = type;
    state.renderedUrl = URL.createObjectURL(blob);
    const extension = type.includes('mp4') ? 'mp4' : 'webm';
    elements.downloadButton.href = state.renderedUrl;
    elements.downloadButton.download = `wzrdvid-lite-${duration}s-${Date.now()}.${extension}`;
    elements.downloadButton.textContent = `DOWNLOAD ${extension.toUpperCase()}`;
    elements.downloadButton.className = 'btn btn-primary';
    elements.downloadButton.removeAttribute('aria-disabled');
    setStatus(`render complete // ${duration} sec target // ${extension.toUpperCase()} ready`);
    log(`render complete: target ${duration}s // frames ${frameCount}/${expectedFrames} // ${(blob.size / 1024 / 1024).toFixed(2)} MB // ${extension}`);
  }

  async function prepareAudioStream(duration) {
    if (!state.audio) return null;
    const audio = state.audio.audio;
    const captureStream = audio.captureStream || audio.mozCaptureStream;
    if (!captureStream) {
      log('audio capture unavailable in this browser; rendering video only');
      return null;
    }
    audio.pause();
    audio.currentTime = 0;
    audio.loop = true;
    audio.volume = 0.92;
    const stream = captureStream.call(audio);
    const track = stream.getAudioTracks()[0];
    if (!track) {
      log('no capturable audio track found; rendering video only');
      return null;
    }
    let fadeTimer = 0;
    let fadeInterval = 0;
    return {
      track,
      start: async () => {
        await audio.play().catch(() => log('audio playback blocked; continuing video render'));
        fadeTimer = window.setTimeout(() => {
          const started = performance.now();
          fadeInterval = window.setInterval(() => {
            const progress = Math.min(1, (performance.now() - started) / 1800);
            audio.volume = Math.max(0.0001, 0.92 * (1 - progress));
            if (progress >= 1) window.clearInterval(fadeInterval);
          }, 80);
        }, Math.max(0, duration - 2.0) * 1000);
      },
      stop: () => {
        window.clearTimeout(fadeTimer);
        window.clearInterval(fadeInterval);
        audio.pause();
        audio.volume = 0.92;
      }
    };
  }

  async function drawFrame(timeline, time, duration, preset, ansiIntervals) {
    const segment = timeline.find((item) => time >= item.start && time < item.start + item.duration) || timeline[timeline.length - 1];
    const localTime = Math.max(0, time - segment.start);
    if (segment.source.kind === 'video') {
      await seekVideo(segment.source.element, segment.sourceStart + localTime);
    }
    drawSource(segment, localTime, time, duration, preset);
    if (isAnsiTime(time, ansiIntervals)) drawAnsi(preset, time);
    applyPresetEffects(preset, time, duration);
  }

  function drawSource(segment, localTime, time, duration, preset) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const source = segment.source.element;
    const maxZoom = 0.18 + preset.punch * 0.48;
    const tunnel = (time % 4.5) / 4.5;
    const punch = (Math.sin(time * 6.2 + segment.seed * 12) > 0.955) ? 0.22 : 0;
    const zoom = 1 + tunnel * maxZoom + punch;
    const wobbleX = Math.sin(time * 7.1 + segment.seed * 6) * preset.tape * 10;
    const wobbleY = Math.cos(time * 5.7 + segment.seed * 8) * preset.tape * 5;
    ctx.save();
    ctx.fillStyle = '#080706';
    ctx.fillRect(0, 0, w, h);
    ctx.translate(w / 2 + wobbleX, h / 2 + wobbleY);
    ctx.scale(zoom, zoom);
    ctx.translate(-w / 2, -h / 2);
    drawCover(source, w, h);
    ctx.restore();
    if (duration - time < 2.2) {
      ctx.fillStyle = `rgba(8, 7, 6, ${1 - Math.max(0, duration - time) / 2.2})`;
      ctx.fillRect(0, 0, w, h);
    }
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
      ctx.fillStyle = '#080706';
      ctx.fillRect(0, 0, w, h);
    }
  }

  function drawAnsi(preset, time) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const cols = preset.grid;
    const rows = Math.max(20, Math.round(cols * h / w * 0.55));
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

  function applyPresetEffects(preset, time, duration) {
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
    drawTapeDamage(preset.tape, time);
    drawScanlines(preset.scanlines);
  }

  function drawTapeDamage(amount, time) {
    const w = elements.canvas.width;
    const h = elements.canvas.height;
    const tears = Math.floor(amount * 7);
    for (let i = 0; i < tears; i += 1) {
      if (Math.random() > amount * 0.42) continue;
      const y = Math.floor(Math.random() * h);
      const height = Math.floor(randomBetween(2, 15));
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
  elements.mediaInput.addEventListener('change', async () => addMediaFiles(Array.from(elements.mediaInput.files || [])));
  elements.audioInput.addEventListener('change', async () => {
    const file = elements.audioInput.files?.[0];
    if (file) await setAudioFile(file);
  });
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

  window.addEventListener('beforeunload', () => {
    revokeRenderedUrl();
    state.media.forEach((item) => URL.revokeObjectURL(item.url));
    if (state.audio?.url) URL.revokeObjectURL(state.audio.url);
  });

  updateRenderButtonCopy();
  drawIdleFrame();
  log('Lite is armed. Files stay local in this browser.');
})();
