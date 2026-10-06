/**
 * ICM pixel-flow-field — vanilla port of the pixel-flow-field ref.
 * Fixed full-page canvas: cells form the text from data-text ("ICM"),
 * drift on a coarse flow lattice, scatter on load, flee the pointer.
 * No deps. Colors resolved from theme tokens each frame-batch.
 * ponytail: square cells only; add circle/cross when a page needs it.
 */
(function () {
  'use strict';
  var canvas = document.getElementById('pixel-field');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  if (!ctx) { document.querySelector('.pixel-bg')?.classList.add('pixel-fallback'); return; }

  var TEXT = canvas.dataset.text || 'ICM';
  var CELL = 9, GAP = 3, MAX_CELLS = 9000, TAU = Math.PI * 2;
  var LATTICE = 4, NOISE_SCALE = 0.19, TIME_SCALE = 0.14, FLOW_TURNS = 1.35;
  var REFORM_MS = 1750, STAGGER = 0.45, WORD_LEAD = 0.16;
  var WAKE_TAU = 0.42, WAKE_GAIN = 3.4, WAKE_CEIL = 2.4, MAX_DT = 0.05;
  var TIERS = 7, RAMP_MID = 0.6;

  var reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  var sampler = document.createElement('canvas');
  var sctx = sampler.getContext('2d', { willReadFrequently: true });

  var W = 1, H = 1, cols = 1, rows = 1, n = 1, step = CELL + GAP, cellPx = CELL;
  var mask, homeX, homeY, scatX, scatY, wakeX, wakeY, delay, ampF, sizeB;
  var latCols = 2, latRows = 2, fU, fV;
  var tierIdx = [], tierCss = [];
  var px = 0, py = 0, ppx = 0, ppy = 0, pActive = false;
  var t0 = performance.now(), last = t0, scatAt = t0, running = false, dead = false;

  function hash2(x, y) {
    var v = Math.sin(x * 127.1 + y * 311.7 + 74.7) * 43758.5453123;
    return v - Math.floor(v);
  }
  function sstep(v) { return v * v * (3 - 2 * v); }
  function vnoise(x, y) {
    var ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    var ux = sstep(fx), uy = sstep(fy);
    var a = hash2(ix, iy), b = hash2(ix + 1, iy), c = hash2(ix, iy + 1), d = hash2(ix + 1, iy + 1);
    return a + (b - a) * ux + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uy;
  }
  // Resolve theme tokens -> rgba. Light/dark adapt on toggle via re-resolve.
  function themeColors() {
    var g = getComputedStyle(document.documentElement);
    function rgb(v, fb) {
      var c = document.createElement('canvas'); c.width = c.height = 1;
      var x = c.getContext('2d'); x.fillStyle = '#000'; x.fillStyle = (g.getPropertyValue(v) || '').trim() || fb;
      x.fillRect(0, 0, 1, 1); var d = x.getImageData(0, 0, 1, 1).data;
      return [d[0], d[1], d[2]];
    }
    return [rgb('--border', '#e4e4e7'), rgb('--accent', '#0891b2'), rgb('--foreground', '#09090b')];
  }
  var palette = themeColors();
  // Re-resolve on theme toggle click (cheap, runs rarely).
  document.getElementById('theme-toggle')?.addEventListener('click', function () {
    setTimeout(function () { palette = themeColors(); buildTiers(); }, 50);
  });

  function ramp(m) {
    var F = palette[0], A = palette[1], I = palette[2];
    var lo = m <= RAMP_MID, f = lo ? F : A, t = lo ? A : I;
    var k = lo ? m / RAMP_MID : (m - RAMP_MID) / (1 - RAMP_MID);
    var al = lo ? 0.24 + (0.92 - 0.24) * k : 0.92 + (1 - 0.92) * k;
    return 'rgba(' + Math.round(f[0] + (t[0] - f[0]) * k) + ',' + Math.round(f[1] + (t[1] - f[1]) * k) + ',' + Math.round(f[2] + (t[2] - f[2]) * k) + ',' + al.toFixed(3) + ')';
  }

  function sample() {
    sampler.width = cols; sampler.height = rows;
    sctx.clearRect(0, 0, cols, rows);
    var fs = Math.max(rows * 0.72, 1);
    sctx.font = '800 ' + fs + 'px Inter, system-ui, sans-serif';
    var w = sctx.measureText(TEXT).width, max = cols * 0.9;
    if (w > max && w > 0) { fs = Math.max(fs * max / w, 1); sctx.font = '800 ' + fs + 'px Inter, system-ui, sans-serif'; }
    sctx.fillStyle = '#fff'; sctx.textAlign = 'center'; sctx.textBaseline = 'middle';
    sctx.fillText(TEXT, cols / 2, rows / 2 + fs * 0.04);
    var d;
    try { d = sctx.getImageData(0, 0, cols, rows).data; } catch (e) { mask.fill(0); return; }
    for (var i = 0; i < n; i++) {
      var p = i * 4, cov = (d[p] / 255) * (d[p + 3] / 255);
      mask[i] = sstep(Math.min(1, Math.max(0, (cov - 0.08) / 0.78)));
    }
  }

  function buildTiers() {
    tierIdx = []; tierCss = [];
    var buckets = []; for (var t = 0; t < TIERS; t++) buckets.push([]);
    for (var i = 0; i < n; i++) buckets[Math.min(TIERS - 1, Math.floor(mask[i] * TIERS))].push(i);
    for (var k = 0; k < TIERS; k++) { tierIdx.push(buckets[k]); tierCss.push(ramp((k + 0.5) / TIERS)); }
  }

  function build() {
    step = Math.max(CELL + GAP, 3); cellPx = CELL;
    cols = Math.max(1, Math.ceil(W / step)); rows = Math.max(1, Math.ceil(H / step));
    if (cols * rows > MAX_CELLS) {
      var s = Math.sqrt(cols * rows / MAX_CELLS); step *= s; cellPx *= s;
      cols = Math.max(1, Math.ceil(W / step)); rows = Math.max(1, Math.ceil(H / step));
    }
    n = cols * rows;
    mask = new Float32Array(n); homeX = new Float32Array(n); homeY = new Float32Array(n);
    scatX = new Float32Array(n); scatY = new Float32Array(n);
    wakeX = new Float32Array(n); wakeY = new Float32Array(n);
    delay = new Float32Array(n); ampF = new Float32Array(n); sizeB = new Float32Array(n);
    latCols = Math.ceil(cols / LATTICE) + 2; latRows = Math.ceil(rows / LATTICE) + 2;
    fU = new Float32Array(latCols * latRows); fV = new Float32Array(latCols * latRows);
    sample();
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) {
      var i = r * cols + c, m = mask[i];
      homeX[i] = (c + 0.5) * step; homeY[i] = (r + 0.5) * step;
      ampF[i] = 1 - m * 0.84; sizeB[i] = 0.3 + 0.64 * m;
      var nx = cols > 1 ? c / (cols - 1) : 0, ny = rows > 1 ? r / (rows - 1) : 0;
      delay[i] = Math.min(1, Math.max(0, nx * 0.55 + ny * 0.3 + hash2(c, r) * 0.15 - m * WORD_LEAD));
      scatX[i] = (hash2(i + 1, 5.3) * 1.25 - 0.125) * W;
      scatY[i] = (hash2(17.7, i + 1) * 1.25 - 0.125) * H;
    }
    buildTiers();
  }

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    var r = canvas.parentElement.getBoundingClientRect();
    W = Math.max(1, r.width); H = Math.max(1, r.height);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
  }

  function flow(t) {
    for (var ly = 0; ly < latRows; ly++) for (var lx = 0; lx < latCols; lx++) {
      var gx = lx * LATTICE * NOISE_SCALE, gy = ly * LATTICE * NOISE_SCALE;
      var sw = vnoise(gx, gy + t), st = vnoise(gx + 37.2, gy - t * 0.8 + 11.5);
      var a = sw * TAU * FLOW_TURNS, mg = 0.35 + 0.65 * st, k = ly * latCols + lx;
      fU[k] = Math.cos(a) * mg; fV[k] = Math.sin(a) * mg;
    }
  }

  function stamp(x, y, dt) {
    var R = 130, lim = R * R, ceil = step * WAKE_CEIL;
    var c0 = Math.max(0, Math.floor((x - R) / step)), c1 = Math.min(cols - 1, Math.ceil((x + R) / step));
    var r0 = Math.max(0, Math.floor((y - R) / step)), r1 = Math.min(rows - 1, Math.ceil((y + R) / step));
    for (var r = r0; r <= r1; r++) for (var c = c0; c <= c1; c++) {
      var i = r * cols + c, dx = homeX[i] - x, dy = homeY[i] - y, q = dx * dx + dy * dy;
      if (q >= lim || q === 0) continue;
      var d = Math.sqrt(q), f = 1 - d / R, push = f * f * R * WAKE_GAIN * dt;
      wakeX[i] = Math.min(ceil, Math.max(-ceil, wakeX[i] + dx / d * push));
      wakeY[i] = Math.min(ceil, Math.max(-ceil, wakeY[i] + dy / d * push));
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    var now = performance.now(), dt = Math.min((now - last) / 1000, MAX_DT); last = now;
    if (reduceMotion) {
      ctx.fillStyle = tierCss[TIERS - 1];
      for (var t = 0; t < TIERS; t++) {
        if (!tierIdx[t].length) continue;
        ctx.fillStyle = tierCss[t]; ctx.beginPath();
        for (var k = 0; k < tierIdx[t].length; k++) {
          var i = tierIdx[t][k], s = cellPx * (sizeB[i] + 0.11);
          if (s > 0.35) ctx.rect(homeX[i] - s / 2, homeY[i] - s / 2, s, s);
        }
        ctx.fill();
      }
      return;
    }
    flow((now - t0) / 1000 * TIME_SCALE);
    if (pActive) {
      var dx = px - ppx, dy = py - ppy, tr = Math.hypot(dx, dy) || 1, st = Math.min(4, Math.max(1, Math.ceil(tr / step)));
      for (var s2 = 1; s2 <= st; s2++) stamp(ppx + dx * s2 / st, ppy + dy * s2 / st, dt / st);
      ppx = px; ppy = py;
    }
    var reform = Math.min((now - scatAt) / REFORM_MS, 1), decay = Math.exp(-dt / WAKE_TAU);
    var drift = step * 0.95, rest = 1 / (1 - STAGGER);
    for (var t2 = 0; t2 < TIERS; t2++) {
      if (!tierIdx[t2].length) continue;
      ctx.fillStyle = tierCss[t2]; ctx.beginPath();
      for (var j = 0; j < tierIdx[t2].length; j++) {
        var m = tierIdx[t2][j];
        var wx = wakeX[m] * decay, wy = wakeY[m] * decay;
        wakeX[m] = wx; wakeY[m] = wy;
        var lx = Math.floor((homeX[m] / step - 0.5) / LATTICE), ly2 = Math.floor((homeY[m] / step - 0.5) / LATTICE);
        lx = Math.min(latCols - 2, Math.max(0, lx)); ly2 = Math.min(latRows - 2, Math.max(0, ly2));
        var ci = ly2 * latCols + lx, fx = 0.5, fy = 0.5;
        var u = (fU[ci] + fV[ci]) / 2, v = (fV[ci] + fV[ci + 1]) / 2;
        var rx = homeX[m] + u * drift * ampF[m] + wx, ry = homeY[m] + v * drift * ampF[m] + wy;
        var sc = 1;
        if (reform < 1) {
          var loc = Math.min(1, Math.max(0, (reform - delay[m] * STAGGER) * rest));
          var e = 1 - Math.pow(1 - loc, 3);
          rx = scatX[m] + (rx - scatX[m]) * e; ry = scatY[m] + (ry - scatY[m]) * e;
          sc = 0.5 + 0.5 * e;
        }
        void fx; void fy; void ci;
        var sz = cellPx * (sizeB[m] + 0.2 * (Math.abs(u) + Math.abs(v))) * sc;
        if (sz > 0.35 && rx > -sz && rx < W + sz && ry > -sz && ry < H + sz) ctx.rect(rx - sz / 2, ry - sz / 2, sz, sz);
      }
      ctx.fill();
    }
  }

  function tick() { if (dead || !running) return; draw(); requestAnimationFrame(tick); }
  function setRun(v) {
    if (v === running || dead) return;
    running = v;
    if (v) { last = performance.now(); requestAnimationFrame(tick); }
  }

  var bg = canvas.parentElement;
  function track(e) {
    var r = canvas.getBoundingClientRect();
    var x = e.clientX - r.left, y = e.clientY - r.top;
    if (!pActive) { ppx = x; ppy = y; }
    px = x; py = y; pActive = true;
  }
  // Listen on window: canvas is pointer-events:none, page scrolls above it.
  window.addEventListener('pointermove', track, { passive: true });
  window.addEventListener('pointerdown', track, { passive: true });
  document.addEventListener('pointerleave', function () { pActive = false; });
  document.addEventListener('visibilitychange', function () {
    setRun(document.visibilityState === 'visible' && !reduceMotion ? true : document.visibilityState === 'visible');
    if (reduceMotion) draw();
  });

  var rT; window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(resize, 150); });
  document.fonts?.ready.then(function () { build(); if (!running) draw(); }).catch(function () {});
  resize();
  if (reduceMotion) { draw(); } else { setRun(true); }
})();
