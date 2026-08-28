((root, factory) => {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.WZRDVID_LITE_CHAOS = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  const CONTRACT_VERSION = 1;
  const MIN_ANSI_CHUNK = 0.5;
  const MAX_ANSI_CHUNK = 3.0;
  const MAX_TIMELINE_SEGMENTS = 240;
  const MAX_ANSI_CELLS = 5600;
  const MIN_ANSI_COLUMNS = 40;
  const MIN_ANSI_ROWS = 20;
  const MIN_ANSI_CELL_WIDTH = 6;
  const MIN_ANSI_CELL_HEIGHT = 10;

  const STRENGTH_FACTORS = Object.freeze({
    low: 0.68,
    medium: 1,
    high: 1.35
  });

  const DENSITY_FACTORS = Object.freeze({
    coarse: 0.72,
    standard: 1,
    fine: 1.35
  });

  function normalizeChoice(value, choices, fallback) {
    const normalized = String(value || '').trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(choices, normalized) ? normalized : fallback;
  }

  function createRng(seed) {
    let value = Number(seed) >>> 0;
    return () => {
      value += 0x6D2B79F5;
      let next = value;
      next = Math.imul(next ^ (next >>> 15), next | 1);
      next ^= next + Math.imul(next ^ (next >>> 7), next | 61);
      return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
    };
  }

  function deriveSeed(projectSeed, domain) {
    let hash = (2166136261 ^ (Number(projectSeed) >>> 0)) >>> 0;
    const value = String(domain);
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619) >>> 0;
    }
    hash ^= hash >>> 16;
    hash = Math.imul(hash, 0x7FEB352D) >>> 0;
    hash ^= hash >>> 15;
    hash = Math.imul(hash, 0x846CA68B) >>> 0;
    return (hash ^ (hash >>> 16)) >>> 0;
  }

  function domainRng(projectSeed, domain) {
    return createRng(deriveSeed(projectSeed, domain));
  }

  function randomBetween(min, max, rng) {
    return min + rng() * (max - min);
  }

  function shuffle(items, rng) {
    for (let index = items.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(rng() * (index + 1));
      [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
    }
    return items;
  }

  function makeRandomTimeline(sources, duration, projectSeed) {
    const rng = domainRng(projectSeed, 'timeline');
    const timeline = [];
    let sourceQueue = [];
    let previousSource = null;
    let time = 0;
    let guard = 0;
    while (time < duration - 0.001 && guard < MAX_TIMELINE_SEGMENTS) {
      guard += 1;
      if (!sourceQueue.length) {
        sourceQueue = shuffle(sources.slice(), rng);
        if (previousSource && sourceQueue.length > 1 && sourceQueue[0] === previousSource) {
          [sourceQueue[0], sourceQueue[1]] = [sourceQueue[1], sourceQueue[0]];
        }
      }
      const source = sourceQueue.shift();
      const isVideo = source.kind === 'video';
      const remainingSources = Math.max(1, sourceQueue.length + 1);
      const coverageBudget = (duration - time) / remainingSources;
      const minVisible = isVideo ? 1.65 : 1.45;
      const maxForCoverage = Math.max(minVisible, coverageBudget * 1.35);
      const candidateDuration = isVideo
        ? randomBetween(1.9, 4.6, rng)
        : randomBetween(1.6, 3.3, rng);
      const segmentDuration = Math.min(candidateDuration, maxForCoverage);
      const safeDuration = Math.min(segmentDuration, duration - time);
      if (safeDuration <= 0.001) break;
      const sourceMax = Math.max(0, (source.duration || safeDuration) - safeDuration);
      timeline.push({
        source,
        start: time,
        duration: safeDuration,
        sourceStart: isVideo ? rng() * sourceMax : 0,
        seed: rng()
      });
      previousSource = source;
      time += safeDuration;
    }
    if (timeline.length) {
      const last = timeline[timeline.length - 1];
      last.duration = Math.max(0, duration - last.start);
    }
    return timeline;
  }

  function makeSequentialTimeline(sources, duration) {
    const timeline = [];
    let time = 0;
    let index = 0;
    let guard = 0;
    while (time < duration - 0.001 && sources.length && guard < MAX_TIMELINE_SEGMENTS) {
      guard += 1;
      const source = sources[index % sources.length];
      index += 1;
      const sourceDuration = Math.max(0.001, source.duration || duration);
      const segmentDuration = source.kind === 'video' ? sourceDuration : 2.4;
      const safeDuration = Math.min(segmentDuration, duration - time);
      if (safeDuration <= 0.001) break;
      timeline.push({
        source,
        start: time,
        duration: safeDuration,
        sourceStart: 0,
        seed: 0.5
      });
      time += safeDuration;
    }
    if (timeline.length) {
      const last = timeline[timeline.length - 1];
      last.duration = Math.max(0, duration - last.start);
    }
    return timeline;
  }

  function makeTimeline(sources, duration, randomize, projectSeed) {
    return randomize
      ? makeRandomTimeline(sources, duration, projectSeed)
      : makeSequentialTimeline(sources, duration);
  }

  function mergeIntervals(intervals, duration) {
    const sorted = intervals
      .map(([start, end]) => [Math.max(0, start), Math.min(duration, end)])
      .filter(([start, end]) => end - start > 0.01)
      .sort((left, right) => left[0] - right[0]);
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

  function buildAnsiIntervals(duration, percent, projectSeed) {
    const clampedPercent = Math.max(0, Math.min(100, Number(percent) || 0));
    if (duration <= 0 || clampedPercent <= 0) return [];
    if (clampedPercent >= 100) return [[0, duration]];

    const rng = domainRng(projectSeed, 'ansi-coverage');
    const chunks = [];
    let time = 0;
    while (time < duration - 0.001) {
      const remaining = duration - time;
      const length = Math.min(remaining, randomBetween(MIN_ANSI_CHUNK, MAX_ANSI_CHUNK, rng));
      chunks.push([time, time + length]);
      time += length;
    }

    shuffle(chunks, rng);
    const target = duration * clampedPercent / 100;
    const selected = [];
    let selectedTotal = 0;
    for (const [start, end] of chunks) {
      if (selectedTotal >= target - 0.05) break;
      const available = end - start;
      const remaining = target - selectedTotal;
      if (available > remaining && remaining >= MIN_ANSI_CHUNK) {
        selected.push([start, Math.min(end, start + remaining)]);
        selectedTotal += remaining;
      } else if (available <= remaining || remaining > available * 0.5) {
        selected.push([start, end]);
        selectedTotal += available;
      }
    }
    return mergeIntervals(selected, duration);
  }

  function bounded(value, maximum) {
    return Math.min(maximum, Math.max(0, Number(value) || 0));
  }

  function rounded(value) {
    return Number(value.toFixed(4));
  }

  function resolveStrength(preset, strength) {
    const normalized = normalizeChoice(strength, STRENGTH_FACTORS, 'medium');
    if (normalized === 'medium') return { ...preset };
    const factor = STRENGTH_FACTORS[normalized];
    return {
      ...preset,
      scanlines: rounded(bounded(preset.scanlines * factor, 0.68)),
      rgb: Math.round(bounded(preset.rgb * factor, 14)),
      tape: rounded(bounded(preset.tape * factor, 0.8)),
      mosaic: rounded(bounded(preset.mosaic * factor, 0.8)),
      punch: rounded(bounded(preset.punch * factor, 0.5))
    };
  }

  function ansiGrid(baseColumns, density, width, height) {
    const normalized = normalizeChoice(density, DENSITY_FACTORS, 'standard');
    const widthLimit = Math.max(MIN_ANSI_COLUMNS, Math.floor(width / MIN_ANSI_CELL_WIDTH));
    const heightLimit = Math.max(MIN_ANSI_ROWS, Math.floor(height / MIN_ANSI_CELL_HEIGHT));
    let columns = Math.max(
      MIN_ANSI_COLUMNS,
      Math.min(widthLimit, Math.round(baseColumns * DENSITY_FACTORS[normalized]))
    );
    let rows = Math.max(MIN_ANSI_ROWS, Math.round(columns * height / width * 0.55));
    while ((columns * rows > MAX_ANSI_CELLS || rows > heightLimit) && columns > MIN_ANSI_COLUMNS) {
      columns -= 1;
      rows = Math.max(MIN_ANSI_ROWS, Math.round(columns * height / width * 0.55));
    }
    return {
      columns,
      rows,
      cells: columns * rows,
      activeDensity: normalized
    };
  }

  function frameChaos(projectSeed, frameIndex) {
    const safeFrame = Math.max(0, Math.floor(Number(frameIndex) || 0));
    const tapeRng = domainRng(projectSeed, `frame:${safeFrame}:tape`);
    const publicRng = domainRng(projectSeed, `frame:${safeFrame}:public-access`);
    return {
      tape: Array.from({ length: 7 }, () => ({
        gate: tapeRng(),
        y: tapeRng(),
        height: tapeRng()
      })),
      publicAccess: Array.from({ length: 8 }, () => ({
        y: publicRng(),
        x: publicRng(),
        width: publicRng(),
        light: publicRng(),
        height: publicRng()
      }))
    };
  }

  function sourceIdentity(source, index) {
    const name = source.id || source.file?.name || `${source.kind || 'media'}-${index + 1}`;
    return `${index + 1}:${source.kind || 'unknown'}:${name}`;
  }

  function finite(value, digits = 6) {
    return Number(Number(value || 0).toFixed(digits));
  }

  function serializeTimeline(timeline, sources) {
    return timeline.map((segment) => ({
      source: sourceIdentity(segment.source, sources.indexOf(segment.source)),
      outputStart: finite(segment.start),
      outputDuration: finite(segment.duration),
      sourceStart: finite(segment.sourceStart),
      visualSeed: finite(segment.seed, 9)
    }));
  }

  function buildPlan(options) {
    const sources = Array.from(options.sources || []);
    const duration = Math.max(0, Number(options.duration) || 0);
    const projectSeed = Number(options.projectSeed) >>> 0;
    const randomize = Boolean(options.randomize);
    const strength = normalizeChoice(options.strength, STRENGTH_FACTORS, 'medium');
    const density = normalizeChoice(options.density, DENSITY_FACTORS, 'standard');
    const timeline = makeTimeline(sources, duration, randomize, projectSeed);
    const ansiIntervals = buildAnsiIntervals(duration, options.ansiPercent, projectSeed);
    const resolvedPreset = resolveStrength(options.preset, strength);
    const grid = ansiGrid(options.preset.grid, density, options.width, options.height);
    const totalFrames = Math.max(1, Math.ceil(duration * options.fps));
    const sampleFrames = Array.from(new Set([0, Math.floor((totalFrames - 1) / 2), totalFrames - 1]));
    const oracle = {
      contractVersion: CONTRACT_VERSION,
      projectSeed,
      sources: sources.map(sourceIdentity),
      settings: {
        duration,
        randomize,
        ansiPercent: Math.max(0, Math.min(100, Number(options.ansiPercent) || 0)),
        preset: options.presetName,
        strength,
        density,
        width: options.width,
        height: options.height,
        fps: options.fps
      },
      timeline: serializeTimeline(timeline, sources),
      ansi: {
        active: ansiIntervals.length > 0,
        intervals: ansiIntervals.map(([start, end]) => [finite(start), finite(end)]),
        grid
      },
      treatment: {
        scanlines: resolvedPreset.scanlines,
        rgb: resolvedPreset.rgb,
        tape: resolvedPreset.tape,
        mosaic: resolvedPreset.mosaic,
        punch: resolvedPreset.punch
      },
      randomVisualSamples: sampleFrames.map((frameIndex) => ({
        frameIndex,
        decisions: frameChaos(projectSeed, frameIndex)
      }))
    };
    return { timeline, ansiIntervals, resolvedPreset, ansiGrid: grid, oracle };
  }

  function seedLabel(projectSeed) {
    if (projectSeed === null || projectSeed === undefined) return 'UNARMED';
    return `#${String((Number(projectSeed) >>> 0) % 1000000).padStart(6, '0')}`;
  }

  return Object.freeze({
    CONTRACT_VERSION,
    STRENGTH_FACTORS,
    DENSITY_FACTORS,
    LIMITS: Object.freeze({
      maxAnsiCells: MAX_ANSI_CELLS,
      minAnsiColumns: MIN_ANSI_COLUMNS,
      minAnsiRows: MIN_ANSI_ROWS,
      minAnsiCellWidth: MIN_ANSI_CELL_WIDTH,
      minAnsiCellHeight: MIN_ANSI_CELL_HEIGHT
    }),
    createRng,
    deriveSeed,
    domainRng,
    makeTimeline,
    buildAnsiIntervals,
    resolveStrength,
    ansiGrid,
    frameChaos,
    buildPlan,
    seedLabel
  });
});
