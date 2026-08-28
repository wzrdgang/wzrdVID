'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const chaos = require('../docs/lite/chaos.js');

const repoRoot = path.resolve(__dirname, '..');
const appSource = fs.readFileSync(path.join(repoRoot, 'docs/lite/app.js'), 'utf8');
const liteHtml = fs.readFileSync(path.join(repoRoot, 'docs/lite/index.html'), 'utf8');
assert.doesNotMatch(appSource, /Math\.random/, 'the Lite runtime must not bypass the deterministic PRNG');
assert.match(appSource, /Promise\.race\(\[\s*stopped\.then\(\(\) => true\)/, 'MediaRecorder finalization must have a bounded fallback');
assert.match(appSource, /mimeType\.includes\('mp4'\).*requestFrame/, 'manual canvas frames must stay on the validated MP4 path');
assert.match(appSource, /if \(!blob\.size\) throw new Error/, 'empty recorder output must never become a download');
assert.match(liteHtml, /id="effectStrength"[\s\S]*value="medium" selected/, 'Effect Strength must default to Medium');
assert.match(liteHtml, /id="ansiDensity"[\s\S]*value="standard" selected/, 'ANSI Text Density must default to Standard');
assert.match(liteHtml, /id="rerollChaos"[\s\S]*disabled/, 'Reroll Chaos must start unarmed');
assert.ok(liteHtml.indexOf('chaos.js') < liteHtml.indexOf('app.js'), 'the deterministic contract must load before the Lite runtime');

const presets = {
  'Chunkcore Chaos': { grid: 74, ramp: '  ░▒▓█', scanlines: 0.34, rgb: 5, tape: 0.34, mosaic: 0.4, punch: 0.28, fps: 30 },
  'Classic ANSI Lite': { grid: 96, ramp: ' .:-=+*#%@', scanlines: 0.2, rgb: 2, tape: 0.12, mosaic: 0.14, punch: 0.16, fps: 30 },
  'VHS Damage Lite': { grid: 84, ramp: '  ░▒▓█', scanlines: 0.46, rgb: 8, tape: 0.58, mosaic: 0.26, punch: 0.22, fps: 30 },
  'Dial-Up Glitch': { grid: 68, ramp: '  ░▒▓█', scanlines: 0.28, rgb: 9, tape: 0.44, mosaic: 0.62, punch: 0.36, fps: 30 },
  'PUBLIC ACCESS': { grid: 88, ramp: ' .:-=+*#%@ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', scanlines: 0.38, rgb: 4, tape: 0.5, mosaic: 0.18, punch: 0.14, fps: 30, profile: 'publicAccess' }
};

const standardGrid = {
  'Chunkcore Chaos': [74, 23],
  'Classic ANSI Lite': [96, 30],
  'VHS Damage Lite': [84, 26],
  'Dial-Up Glitch': [68, 21],
  'PUBLIC ACCESS': [88, 27]
};

const sources = [
  { id: 'symbolic-still-a', kind: 'image', duration: 2.4 },
  { id: 'symbolic-video-b', kind: 'video', duration: 7.25 },
  { id: 'symbolic-still-c', kind: 'image', duration: 2.4 }
];

function plan(overrides = {}) {
  const presetName = overrides.presetName || 'Chunkcore Chaos';
  return chaos.buildPlan({
    sources,
    duration: 15,
    randomize: true,
    ansiPercent: 70,
    projectSeed: 423624705,
    presetName,
    preset: presets[presetName],
    strength: 'medium',
    density: 'standard',
    width: 854,
    height: 480,
    fps: 30,
    ...overrides
  });
}

const first = plan();
const repeated = plan();
assert.deepEqual(first.oracle, repeated.oracle, 'same seed + same inputs must produce the same semantic plan');
assert.notDeepEqual(first.oracle, plan({ projectSeed: 423624706 }).oracle, 'rerolled seed must change the semantic plan');

for (const [name, preset] of Object.entries(presets)) {
  assert.deepEqual(chaos.resolveStrength(preset, 'medium'), preset, `${name} Medium must equal the pre-control preset`);
  const low = chaos.resolveStrength(preset, 'low');
  const high = chaos.resolveStrength(preset, 'high');
  for (const key of ['scanlines', 'rgb', 'tape', 'mosaic', 'punch']) {
    assert.ok(low[key] <= preset[key], `${name} Low ${key} must not exceed Medium`);
    assert.ok(high[key] >= preset[key], `${name} High ${key} must not undercut Medium`);
  }

  const coarse = chaos.ansiGrid(preset.grid, 'coarse', 854, 480);
  const standard = chaos.ansiGrid(preset.grid, 'standard', 854, 480);
  const fine = chaos.ansiGrid(preset.grid, 'fine', 854, 480);
  assert.deepEqual([standard.columns, standard.rows], standardGrid[name], `${name} Standard must equal the pre-control ANSI grid`);
  assert.ok(coarse.columns < standard.columns && standard.columns < fine.columns, `${name} density ordering must be visible`);
  for (const grid of [coarse, standard, fine]) {
    assert.ok(grid.cells <= chaos.LIMITS.maxAnsiCells, `${name} must stay inside the ANSI cell cap`);
    assert.ok(grid.columns >= chaos.LIMITS.minAnsiColumns, `${name} must stay above the ANSI column floor`);
    assert.ok(grid.rows >= chaos.LIMITS.minAnsiRows, `${name} must stay above the ANSI row floor`);
  }
}

const coarsePlan = plan({ density: 'coarse' }).oracle;
const finePlan = plan({ density: 'fine' }).oracle;
assert.deepEqual(coarsePlan.timeline, finePlan.timeline, 'density must not alter timeline randomness');
assert.deepEqual(coarsePlan.ansi.intervals, finePlan.ansi.intervals, 'density must not alter ANSI coverage scheduling');
assert.deepEqual(coarsePlan.randomVisualSamples, finePlan.randomVisualSamples, 'density must not alter frame chaos');
assert.notDeepEqual(coarsePlan.ansi.grid, finePlan.ansi.grid, 'density must alter ANSI grid workload');

const lowPlan = plan({ strength: 'low' }).oracle;
const highPlan = plan({ strength: 'high' }).oracle;
assert.deepEqual(lowPlan.timeline, highPlan.timeline, 'strength must not alter timeline randomness');
assert.deepEqual(lowPlan.ansi, highPlan.ansi, 'strength must not alter ANSI scheduling or density');
assert.deepEqual(lowPlan.randomVisualSamples, highPlan.randomVisualSamples, 'strength must not alter raw random decisions');
assert.notDeepEqual(lowPlan.treatment, highPlan.treatment, 'strength must alter bounded treatment parameters');

const zeroAnsi = plan({ ansiPercent: 0, density: 'fine' }).oracle;
assert.equal(zeroAnsi.ansi.active, false, '0% ANSI must keep every frame on the normal path');
assert.deepEqual(zeroAnsi.ansi.intervals, [], '0% ANSI must schedule no ANSI intervals');
assert.deepEqual(plan({ ansiPercent: 100 }).oracle.ansi.intervals, [[0, 15]], '100% ANSI must cover the full output');

for (const duration of [15, 30, 60]) {
  for (const [quality, dimensions] of Object.entries({ fast: [854, 480, 30], better: [1280, 720, 24] })) {
    for (const presetName of Object.keys(presets)) {
      const candidate = plan({
        duration,
        presetName,
        preset: presets[presetName],
        width: dimensions[0],
        height: dimensions[1],
        fps: dimensions[2]
      }).oracle;
      assert.equal(candidate.settings.duration, duration, `${quality}/${presetName} must preserve duration`);
      assert.ok(candidate.timeline.length > 0, `${quality}/${presetName} must create a timeline`);
      assert.ok(candidate.ansi.grid.cells <= chaos.LIMITS.maxAnsiCells, `${quality}/${presetName} must respect the cell cap`);
    }
  }
}

assert.equal(chaos.seedLabel(null), 'UNARMED');
assert.match(chaos.seedLabel(423624705), /^#[0-9]{6}$/);
console.log('Lite deterministic chaos contract: PASS');
