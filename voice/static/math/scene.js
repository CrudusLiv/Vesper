// voice/static/math/scene.js
// Pure-math 2D figure for ui_render_mode === 'math'. No three.js, no assets:
// every line is a function of time, state and the speech envelope.
// Proportions are traced from voice/static/face/vesper.png (1 unit = 8px of the
// 1250px-tall source, origin at the image centre, y down).
if (typeof VESPER_RENDER_MODE !== 'undefined' && VESPER_RENDER_MODE === 'math') {
  const { startEnvelope, mouthWeightAt } = await import('/static/face/lipsync.js');

  const cv = document.createElement('canvas');
  cv.id = 'vesper-math-canvas';
  cv.style.zIndex = 1;
  cv.style.pointerEvents = 'none';
  document.body.appendChild(cv);
  // The figure is drawn on `fig`; in glyph mode (default) it is then re-read as
  // a character grid onto the visible canvas. ?plain=1 shows the raw line art.
  const GLYPHS = new URLSearchParams(location.search).get('plain') !== '1';
  const out = cv.getContext('2d');
  const fig = GLYPHS ? document.createElement('canvas') : cv;
  const figCtx = fig.getContext('2d');
  let ctx = figCtx;  // swapped to `out` once the glyph layer is down, for the crisp face details
  const glc = document.createElement('canvas');
  const gl = glc.getContext('webgl', { premultipliedAlpha: true });
  const small = document.createElement('canvas');
  const sctx = small.getContext('2d', { willReadFrequently: true });
  sctx.imageSmoothingQuality = 'high';
  const CW = 5, CH = 8;
  const RAMP = ['.', ':', 'i', 'l', 'o', 'c', 'Z', 'O', 'Q', 'B', '@'];
  let W, H, U, dpr, fdpr, cols, rows;
  function resize() {
    dpr = Math.min(devicePixelRatio, 2); fdpr = GLYPHS ? 1 : dpr;
    W = innerWidth; H = innerHeight; U = Math.min(W, H * 0.78) / 100;
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    fig.width = W * fdpr; fig.height = H * fdpr;
    glc.width = W; glc.height = H;
    cols = Math.ceil(W / CW); rows = Math.ceil(H / CH);
    small.width = cols; small.height = rows;
  }
  addEventListener('resize', resize);
  resize();

  const PAL = { silver: '218,222,232', lilac: '170,150,225', gold: '214,178,74', accent: '150,110,200', lime: '196,214,92', danger: '220,70,80' };
  // glow: overall line alpha; sway: hair/cloth motion; rgb: embroidery + watch glow
  const STATE = {
    idle:      { glow: 0.8, sway: 1.0, rgb: PAL.silver },
    listening: { glow: 1.0, sway: 0.6, rgb: PAL.lime },
    thinking:  { glow: 1.0, sway: 1.6, rgb: PAL.danger },
    speaking:  { glow: 1.0, sway: 1.3, rgb: PAL.accent },
    error:     { glow: 1.0, sway: 3.0, rgb: PAL.danger },
  };
  let state = 'idle';
  const cur = { glow: 0.8, sway: 1.0 };
  let amp = 0, mouth = 0, viseme = null;

  addEventListener('vesper:state', (e) => { if (STATE[e.detail]) state = e.detail; });
  addEventListener('vesper:amplitude', (e) => { amp = Math.min((e.detail || 0) * 10, 1); });
  addEventListener('vesper:viseme', (e) => {
    viseme = startEnvelope(e.detail.envelope, e.detail.interval_ms, performance.now());
  });

  const lerp = (a, b, k) => a + (b - a) * k;
  // Cheap smooth noise: incommensurate sines never visibly repeat.
  const noise = (x, t) => Math.sin(x * 1.7 + t) * 0.5 + Math.sin(x * 3.1 - t * 1.3) * 0.3 + Math.sin(x * 5.3 + t * 0.7) * 0.2;

  function stroke(rgb, a, w) { ctx.strokeStyle = `rgba(${rgb},${a})`; ctx.lineWidth = w; ctx.stroke(); }
  function poly(pts) {
    ctx.beginPath();
    pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  }

  const FACE = { cy: -28.2, rx: 8.4, ry: 13 };
  const EYE_Y = -25.6, MOUTH_Y = -17.2;
  const HAIR = { cy: -30, rx: 10.5, ry: 19 };

  // One hair lock as a cubic Bezier: scalp -> face edge -> chest/shoulder.
  function lock(sig, k, sway, t, i, reach) {
    const phi = k * 1.45;
    const x0 = sig * Math.sin(phi) * HAIR.rx, y0 = HAIR.cy - Math.cos(phi) * HAIR.ry;
    const n = noise(i * 0.9, t * 0.7) * sway;
    const x3 = sig * (10.5 + 17 * k * reach) + n * 1.6, y3 = 26 + 16 * k + Math.sin(t * 0.9 + i) * 0.6 * sway;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.bezierCurveTo(x0 * 1.05, y0 + 15, sig * (9 + 19 * k * reach) + n * 0.8, -4 + 6 * k, x3, y3);
  }

  const SPARKS = Array.from({ length: 90 }, () => ({
    x: Math.random(), y: Math.random(), ph: Math.random() * 6.28, sp: 0.6 + Math.random() * 1.6, s: 2 + Math.random() * 5,
  }));
  const colorCache = new Map();
  const glyphColor = (key) => {
    let c = colorCache.get(key);
    if (!c) { c = `rgb(${(key >> 8) * 17},${((key >> 4) & 15) * 17},${(key & 15) * 17})`; colorCache.set(key, c); }
    return c;
  };

  // Re-read the figure canvas as a character grid: coverage picks the glyph,
  // the figure's own pixel colour tints it, a slow noise field makes it shimmer.
  function glyphPass(t, rgb, under = 0) {
    sctx.clearRect(0, 0, cols, rows);
    sctx.drawImage(fig, 0, 0, cols, rows);
    const data = sctx.getImageData(0, 0, cols, rows).data;
    out.setTransform(dpr, 0, 0, dpr, 0, 0);
    out.clearRect(0, 0, W, H);
    out.globalAlpha = 1;
    if (under) { out.globalAlpha = under; out.drawImage(fig, 0, 0, W, H); out.globalAlpha = 0.55; }
    out.font = `${CH}px "IBM Plex Mono", monospace`;
    out.textAlign = 'center'; out.textBaseline = 'middle';
    let lastKey = -1;
    const occupied = new Uint8Array(cols * rows);
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const i = (y * cols + x) * 4, a = data[i + 3];
        if (a < 4) continue;
        const luma = (data[i] * 0.3 + data[i + 1] * 0.59 + data[i + 2] * 0.11) / 255;
        const lv = Math.min(1, Math.min(1, Math.pow(a / 255 * 9, 0.75)) * (0.2 + luma * 1.1) + noise(x * 0.35 + y * 0.21, t * 1.8) * 0.1);
        if (lv < 0.1) continue;
        occupied[y * cols + x] = 1;
        const s = 0.4 + 0.6 * lv;
        const key = ((data[i] * s) >> 4) << 8 | ((data[i + 1] * s) >> 4) << 4 | ((data[i + 2] * s) >> 4);
        if (key !== lastKey) { out.fillStyle = glyphColor(key); lastKey = key; }
        out.fillText(RAMP[Math.min(RAMP.length - 1, (lv * RAMP.length) | 0)], x * CW + CW / 2, y * CH + CH / 2);
      }
    }
    // Sparkles: twinkling crosses, only where the grid is empty.
    out.globalAlpha = 1;
    out.lineWidth = 0.8;
    for (const p of SPARKS) {
      const px = p.x * W, py = p.y * H;
      if (occupied[((py / CH) | 0) * cols + ((px / CW) | 0)]) continue;
      const k = Math.max(0, Math.sin(t * p.sp + p.ph)) ** 3;
      if (k < 0.05) continue;
      const r = p.s * k;
      out.strokeStyle = `rgba(${p.s > 5 ? rgb : PAL.silver},${0.2 + 0.7 * k})`;
      out.beginPath(); out.moveTo(px - r, py); out.lineTo(px + r, py); out.moveTo(px, py - r * 1.3); out.lineTo(px, py + r * 1.3); out.stroke();
    }
  }

  // The painted portrait is the source of truth for her look; the math only
  // animates it (sway, breathing, glow, glyph shimmer). The vector figure below
  // is the fallback when the PNG is missing.
  const img = new Image();
  let imgReady = false;
  img.onload = () => { imgReady = initGL(); };
  img.src = VESPER_FACE_URL;

  // GPU mesh warp: the portrait is a grid whose vertices are displaced by the
  // math below, so head, hair, robe and chest each move on their own.
  const VS = `
    attribute vec2 aUv;
    uniform vec4 uRect; uniform vec2 uRes, uImg;
    uniform float uT, uSway, uTh, uBob, uErr;
    uniform sampler2D uTex;
    varying vec2 vUv;
    float luma(vec2 uv) { return dot(texture2D(uTex, uv).rgb, vec3(.3, .59, .11)); }
    void main() {
      vUv = aUv;
      vec2 p = aUv * uImg;
      float l = (luma(aUv) + luma(aUv + vec2(.012, 0.)) + luma(aUv - vec2(.012, 0.)) + luma(aUv + vec2(0., .01)) + luma(aUv - vec2(0., .01))) * .2;
      float hair = smoothstep(.45, .75, l);
      float head = 1. - smoothstep(380., 560., p.y);
      float hang = smoothstep(330., 1250., p.y);
      vec2 pv = vec2(385., 520.), d = p - pv;
      float a = uTh * head;
      p = pv + vec2(d.x * cos(a) - d.y * sin(a), d.x * sin(a) + d.y * cos(a));
      p.y -= uBob * head;
      p.x += sin(p.y * .011 + uT * .9 + p.x * .006) * 14. * hang * hang * hair * uSway;
      p.x += sin(p.y * .008 - uT * .5) * 3. * hang * (1. - hair) * uSway;
      float chest = smoothstep(480., 640., p.y) * (1. - smoothstep(900., 1100., p.y));
      p.y += sin(uT * 1.1) * 5. * chest;
      p.x += (p.x - 385.) * sin(uT * 1.1) * .004 * chest;
      if (uErr > 0.) {
        float r = fract(sin(floor(p.y / 18.) * 91.3 + floor(uT * 14.)) * 437.5);
        p.x += step(.94, r) * (r - .97) * 900. * uErr;
      }
      vec2 px = uRect.xy + p * (uRect.zw / uImg);
      gl_Position = vec4(px.x / uRes.x * 2. - 1., 1. - px.y / uRes.y * 2., 0., 1.);
    }`;
  const FS = 'precision mediump float; uniform sampler2D uTex; varying vec2 vUv; void main() { gl_FragColor = texture2D(uTex, vUv); }';
  const GU = {};
  let glCount = 0;
  function initGL() {
    if (!gl) return false;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    gl.useProgram(prog);
    const GX = 36, GY = 58, uv = [], idx = [];
    for (let y = 0; y <= GY; y++) for (let x = 0; x <= GX; x++) uv.push(x / GX, y / GY);
    for (let y = 0; y < GY; y++) for (let x = 0; x < GX; x++) {
      const i = y * (GX + 1) + x;
      idx.push(i, i + 1, i + GX + 1, i + 1, i + GX + 2, i + GX + 1);
    }
    glCount = idx.length;
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(uv), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'aUv');
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
    gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    for (const n of ['uRect', 'uRes', 'uImg', 'uT', 'uSway', 'uTh', 'uBob', 'uErr']) GU[n] = gl.getUniformLocation(prog, n);
    return true;
  }
  function drawWarped(x0, y0, iw, ih, sw, th, bob) {
    gl.viewport(0, 0, glc.width, glc.height);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform4f(GU.uRect, x0, y0, iw, ih); gl.uniform2f(GU.uRes, W, H); gl.uniform2f(GU.uImg, img.width, img.height);
    gl.uniform1f(GU.uT, t); gl.uniform1f(GU.uSway, sw); gl.uniform1f(GU.uTh, th); gl.uniform1f(GU.uBob, bob);
    gl.uniform1f(GU.uErr, state === 'error' ? 1 : 0);
    gl.drawElements(gl.TRIANGLES, glCount, gl.UNSIGNED_SHORT, 0);
  }
  const EYES = [[330, 305], [463, 305]], WATCH = [383, 1085], HEAD = [385, 270];
  let lean = 0;

  function imageFrame(g, sw, rgb) {
    lean += ((state === 'listening' ? 1 : 0) - lean) * 0.06;
    const s = H * 0.94 * (1 + 0.012 * lean) / img.height, iw = img.width * s, x0 = (W - iw) / 2;
    const y0 = H * 0.03 - mouth * 2 - lean * 3;
    figCtx.setTransform(1, 0, 0, 1, 0, 0);
    figCtx.clearRect(0, 0, W, H);
    const th = Math.sin(t * 0.6) * 0.012 * sw + lean * 0.03, bob = mouth * 6;
    drawWarped(x0, y0, iw, img.height * s, sw, th, bob);
    figCtx.drawImage(glc, 0, 0);
    // Overlay anchors follow the head through the same rotation/bob as the shader.
    const at = (px, py) => {
      const c = Math.cos(th), sn = Math.sin(th), dx = px - 385, dy = py - 520;
      return [x0 + (385 + dx * c - dy * sn) * s, y0 + (520 + dx * sn + dy * c - bob) * s];
    };
    figCtx.globalCompositeOperation = 'lighter';
    const glow = (sx, sy, r, c, a) => {
      const [gx, gy] = at(sx, sy), rr = r * s;
      const gr = figCtx.createRadialGradient(gx, gy, 0, gx, gy, rr);
      gr.addColorStop(0, `rgba(${c},${a})`); gr.addColorStop(1, `rgba(${c},0)`);
      figCtx.fillStyle = gr; figCtx.fillRect(gx - rr, gy - rr, rr * 2, rr * 2);
    };
    // Eyes widen listening, narrow thinking, breathe otherwise; the watch pulses with speech.
    const dil = state === 'listening' ? 1.5 : state === 'thinking' ? 0.7 : 1 + 0.2 * Math.sin(t * 0.8) + mouth * 0.5;
    for (const [ex, ey] of EYES) glow(ex, ey, 36 * dil, PAL.gold, 0.3);
    glow(WATCH[0], WATCH[1], 80, rgb, 0.18 + mouth * 0.5);
    // Listening: rings contract onto her; speaking: they radiate out with the voice.
    if (state === 'listening' || state === 'speaking') {
      const inward = state === 'listening', rate = inward ? 0.45 : 0.3 + mouth * 0.5;
      for (let k = 0; k < 3; k++) {
        const ph = ((t * rate + k / 3) % 1 + 1) % 1, p = inward ? 1 - ph : ph;
        figCtx.beginPath();
        figCtx.ellipse(...at(HEAD[0], HEAD[1]), (80 + p * 260) * s, (100 + p * 320) * s, 0, 0, Math.PI * 2);
        figCtx.strokeStyle = `rgba(${rgb},${0.5 * (1 - ph) * (inward ? 1 : 0.4 + mouth)})`;
        figCtx.lineWidth = 6 * s; figCtx.stroke();
      }
    }
    // Thinking: motes orbit her head.
    if (state === 'thinking') {
      for (let i = 0; i < 9; i++) {
        const a = t * 1.3 + i * Math.PI * 2 / 9;
        glow(HEAD[0] + Math.cos(a) * 230, HEAD[1] + Math.sin(a) * 290 * (0.6 + 0.4 * Math.sin(t + i)), 26, rgb, 0.7);
      }
    }
    if (state === 'error') {
      figCtx.fillStyle = `rgba(${PAL.danger},${0.12 + 0.1 * Math.sin(t * 14)})`;
      figCtx.fillRect(0, 0, W, H);
    }
    figCtx.globalCompositeOperation = 'source-over';
    // Lids: blink every ~4.3s; thinking keeps them half shut.
    const blink = 1 - Math.max(0, 1 - Math.abs(((t % 4.3) - 0.1) * 9));
    const shut = Math.max(1 - blink, state === 'thinking' ? 0.55 : 0);
    if (shut > 0.04) {
      figCtx.fillStyle = 'rgb(232,222,232)';
      for (const [ex, ey] of EYES) {
        figCtx.beginPath();
        figCtx.ellipse(...at(ex, ey), 40 * s, 24 * shut * s, th, 0, Math.PI * 2);
        figCtx.fill();
      }
    }
    if (mouth > 0.03) {
      figCtx.beginPath();
      figCtx.ellipse(...at(385, 383), (11 + mouth * 5) * s, (2 + mouth * 10) * s, th, 0, Math.PI * 2);
      figCtx.fillStyle = 'rgba(70,28,44,0.92)'; figCtx.fill();
    }
    glyphPass(gt, rgb, 0.7);
  }

  let t = 0, last = performance.now(), gt = 0;  // gt: glyph-shimmer clock, runs fast while thinking
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.05); last = now; t += dt; gt += dt * (state === 'thinking' ? 4 : 1);
    const def = STATE[state];
    const k = 1 - Math.exp(-dt * 4);
    cur.glow = lerp(cur.glow, def.glow, k); cur.sway = lerp(cur.sway, def.sway, k);
    const vis = viseme ? mouthWeightAt(viseme, now) : 0;
    mouth = lerp(mouth, Math.max(vis, state === 'speaking' ? amp : 0), 1 - Math.exp(-dt * 18));
    const g = cur.glow, sw = cur.sway, rgb = def.rgb;
    const jitter = state === 'error' ? (Math.random() - 0.5) * 0.6 * U : 0;

    if (GLYPHS && imgReady) { imageFrame(g, sw, rgb); return; }

    ctx = figCtx;
    ctx.setTransform(fdpr, 0, 0, fdpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.translate(W / 2 + jitter, H * 0.48 + Math.sin(t * 1.1) * 0.18 * U);
    ctx.scale(U, U);
    ctx.lineCap = 'round';

    const hairGrad = ctx.createLinearGradient(0, -49, 0, 44);
    hairGrad.addColorStop(0, `rgb(${PAL.silver})`);
    hairGrad.addColorStop(0.3, `rgb(${PAL.silver})`);
    hairGrad.addColorStop(0.8, `rgb(${PAL.lilac})`);

    // Back hair: wider, dimmer spill behind the shoulders.
    ctx.strokeStyle = hairGrad; ctx.lineWidth = 0.1;
    for (const sig of [-1, 1]) for (let i = 0; i < 22; i++) {
      const kk = i / 21;
      ctx.globalAlpha = (0.08 + 0.1 * kk) * g;
      lock(sig, kk, sw, t, i + 100 * (sig + 1), 1.55);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Robe: one silhouette path, vertical charcoal gradient.
    ctx.beginPath();
    ctx.moveTo(-7.6, -9.5);
    ctx.bezierCurveTo(-13, -9, -18, -8, -21, -4.5);
    ctx.bezierCurveTo(-27, 0, -28.5, 20, -27.5, 50);
    ctx.lineTo(27.5, 50);
    ctx.bezierCurveTo(28.5, 20, 27, 0, 21, -4.5);
    ctx.bezierCurveTo(18, -8, 13, -9, 7.6, -9.5);
    ctx.closePath();
    const robe = ctx.createLinearGradient(0, -10, 0, 50);
    robe.addColorStop(0, 'rgb(46,46,60)'); robe.addColorStop(1, 'rgb(17,17,25)');
    ctx.fillStyle = robe; ctx.fill();
    stroke(PAL.silver, 0.4 * g, 0.16);

    // Sleeve folds: slow sine ripples; arm/torso gap lines.
    for (const sig of [-1, 1]) {
      for (let j = 0; j < 4; j++) {
        const pts = [];
        for (let y = -2; y <= 50; y += 1.5) {
          pts.push([sig * (18 + j * 2.6 + (y / 50) * 1.4 + Math.sin(y * 0.12 + j * 1.7 + t * 0.4) * 0.55 * sw), y]);
        }
        poly(pts); stroke(PAL.silver, (0.1 + 0.03 * j) * g, 0.1);
      }
      ctx.beginPath(); ctx.moveTo(sig * 15.5, 2);
      ctx.bezierCurveTo(sig * 18, 18, sig * 14, 35, sig * 13.5, 50);
      stroke(PAL.silver, 0.3 * g, 0.14);
    }

    // Waist gather: short wavering ticks on a sagging line.
    for (let x = -12; x <= 12.5; x += 1.1) {
      ctx.beginPath();
      ctx.moveTo(x, 29.2 + (x / 12) ** 2 * 0.6);
      ctx.lineTo(x + Math.sin(t * 0.8 + x) * 0.15, 32.4 + (x / 12) ** 2 * 0.6);
      stroke(PAL.silver, 0.26 * g, 0.09);
    }

    // Embroidery: central stem with leaf pairs, polar-rose medallions.
    ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(0, 24);
    stroke(rgb, 0.3 * g, 0.1);
    for (let y = -6; y < 24; y += 3.4) {
      const l = 2.6 * (1 - (y + 6) / 44);
      for (const sig of [-1, 1]) {
        ctx.beginPath(); ctx.moveTo(0, y);
        ctx.quadraticCurveTo(sig * l * 0.8, y - 1.4 - l * 0.3, sig * l * 1.5, y - 0.4 + Math.sin(t + y) * 0.15);
        stroke(rgb, 0.35 * g, 0.1);
      }
    }
    [[-3.8, 3.2, 6], [5.5, 3.6, 8], [14.5, 3.0, 6], [22, 2.2, 6]].forEach(([cy, size, petals], m) => {
      const pts = [], spin = t * 0.12 * (m % 2 ? 1 : -1);
      for (let a = 0; a <= Math.PI * 2 + 0.05; a += 0.06) {
        const r = size * (0.45 + 0.55 * Math.abs(Math.cos(petals * 0.5 * a + spin)));
        pts.push([Math.cos(a) * r, cy + Math.sin(a) * r]);
      }
      poly(pts); stroke(rgb, (0.42 + mouth * 0.4) * g, 0.1);
    });

    // High collar with trim.
    poly([[-5, -15.5], [5, -15.5], [7.6, -9.2], [-7.6, -9.2]]);
    ctx.fillStyle = '#07070c'; ctx.fill(); stroke(PAL.silver, 0.5 * g, 0.14);
    poly([[-4.4, -14.6], [4.4, -14.6], [6.6, -10.2], [-6.6, -10.2]]);
    stroke(PAL.silver, 0.25 * g, 0.09);

    // Chain and pocket watch: V of sagging links to a gold watch with live hands.
    const swing = Math.sin(t * 1.3) * 0.3;
    const wx = swing * 0.5, wy = 37;
    for (const sig of [-1, 1]) {
      const pts = [];
      for (let f = 0; f <= 1.0001; f += 0.05) {
        pts.push([sig * 8.2 * (1 - f) + wx * f * f, -8.5 + f * (wy - 3.4 + 8.5) + Math.sin(f * Math.PI) * -1.2]);
      }
      poly(pts); stroke(PAL.silver, 0.45 * g, 0.12);
    }
    const drawWatch = () => {
    ctx.save();
    ctx.translate(wx, wy);
    ctx.rotate(swing * 0.06);
    ctx.beginPath(); ctx.arc(0, -4.2, 0.7, 0, Math.PI * 2); stroke(PAL.gold, 0.9, 0.18);
    ctx.shadowColor = `rgba(${rgb},${0.35 + mouth * 0.6})`; ctx.shadowBlur = 5 + mouth * 14;
    ctx.beginPath(); ctx.arc(0, 0, 3.4, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(232,232,238,0.88)'; ctx.fill();
    stroke(PAL.gold, 0.95, 0.35);
    ctx.shadowBlur = 0;
    for (let h = 0; h < 12; h++) {
      const a = h * Math.PI / 6, r0 = h % 3 ? 2.7 : 2.4;
      ctx.beginPath(); ctx.moveTo(Math.sin(a) * r0, -Math.cos(a) * r0); ctx.lineTo(Math.sin(a) * 3, -Math.cos(a) * 3);
      stroke('60,55,60', 0.8, 0.1);
    }
    const d = new Date(), mins = d.getMinutes() + d.getSeconds() / 60, hrs = (d.getHours() % 12) + mins / 60;
    for (const [ang, len, w] of [[hrs / 12 * Math.PI * 2, 1.7, 0.2], [mins / 60 * Math.PI * 2, 2.5, 0.14]]) {
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.sin(ang) * len, -Math.cos(ang) * len);
      stroke('40,36,40', 0.95, w);
    }
    ctx.restore();
    };

    // Front hair: long straight locks either side of the face, lilac toward the ends.
    ctx.strokeStyle = hairGrad; ctx.lineWidth = 0.11;
    for (const sig of [-1, 1]) for (let i = 0; i < 34; i++) {
      const kk = i / 33;
      ctx.globalAlpha = (0.25 + 0.4 * (1 - kk)) * g;
      lock(sig, kk, sw, t, i + 50 * (sig + 1), 1);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Face: pale fill, tapered jaw.
    const face = [];
    for (let a = 0; a <= Math.PI * 2 + 0.05; a += 0.1) {
      const c = Math.cos(a), s = Math.sin(a);
      face.push([FACE.rx * c * (s > 0 ? 1 - 0.46 * Math.pow(s, 2.2) : 1), FACE.cy + FACE.ry * s]);
    }
    poly(face); ctx.closePath();
    ctx.fillStyle = '#0b0b12'; ctx.fill();
    ctx.fillStyle = `rgba(236,232,246,${0.55 * g})`; ctx.fill();
    stroke(PAL.silver, 0.6 * g, 0.16);

    if (GLYPHS) {
      glyphPass(t, rgb);
      ctx = out;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.translate(W / 2 + jitter, H * 0.48 + Math.sin(t * 1.1) * 0.18 * U);
      ctx.scale(U, U);
      ctx.lineCap = 'round';
      poly(face); ctx.closePath();
      ctx.fillStyle = `rgba(238,234,248,${0.42 * g})`; ctx.fill();
      stroke(PAL.silver, 0.7 * g, 0.16);
    }
    drawWatch();

    // Bangs: a few strands sweep off the part across the forehead.
    ctx.strokeStyle = `rgb(${PAL.silver})`; ctx.lineWidth = 0.1;
    for (const sig of [-1, 1]) for (let i = 0; i < 6; i++) {
      ctx.globalAlpha = (0.75 - i * 0.06) * g;
      ctx.beginPath(); ctx.moveTo(sig * 0.3, -41);
      ctx.quadraticCurveTo(sig * (4 + i * 0.7), -39 + i * 0.5, sig * (8 + i * 0.2) + noise(i, t * 0.6) * 0.3 * sw, -30 + i * 0.9);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Brows, nose.
    for (const sig of [-1, 1]) {
      ctx.beginPath(); ctx.moveTo(sig * 2.6, EYE_Y - 3.1); ctx.quadraticCurveTo(sig * 5.6, EYE_Y - 4.4, sig * 8, EYE_Y - 3.2);
      stroke('90,86,110', 0.55 * g, 0.12);
    }
    ctx.beginPath(); ctx.moveTo(0, -22.8); ctx.lineTo(0.15, -21.9); stroke('120,110,130', 0.6 * g, 0.1);

    // Eyes: heavy-lidded gold almonds, blinking; listening opens them, thinking drifts the gaze.
    const blink = 1 - Math.max(0, 1 - Math.abs(((t % 4.3) - 0.1) * 9));
    const open = (0.55 + (state === 'listening' ? 0.3 : 0) + mouth * 0.1) * Math.max(0.08, blink);
    const gaze = state === 'thinking' ? Math.sin(t * 0.9) * 0.7 : Math.sin(t * 0.3) * 0.15;
    // Pupil dilation: widens listening, contracts thinking, breathes slowly otherwise.
    const dil = state === 'listening' ? 1.7 : state === 'thinking' ? 0.65 : 1 + 0.35 * Math.sin(t * 0.8) + mouth * 0.5;
    for (const sig of [-1, 1]) {
      ctx.save();
      ctx.translate(sig * 5.6, EYE_Y);
      ctx.beginPath(); ctx.moveTo(-3.4, 0.3);
      ctx.quadraticCurveTo(0, -1.9 * open, 3.4, 0.2);
      ctx.quadraticCurveTo(0, 1.6 * open, -3.4, 0.3);
      ctx.fillStyle = `rgba(${PAL.gold},${0.92 * Math.min(1, g + 0.1)})`;
      ctx.shadowColor = `rgba(${PAL.gold},0.55)`; ctx.shadowBlur = 6;
      ctx.fill(); ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.ellipse(gaze, 0.1, 0.55 * dil, 0.55 * dil * Math.min(1, open * 1.4), 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(20,16,12,0.9)'; ctx.fill();
      ctx.beginPath(); ctx.moveTo(-3.6, 0.4); ctx.quadraticCurveTo(0, -2.1 * open, 3.6, 0.2);
      stroke('14,12,18', 0.95, 0.3);
      ctx.restore();
    }

    // Mouth: a small flat line that opens with the speech envelope.
    ctx.beginPath();
    ctx.ellipse(0, MOUTH_Y, 1.3 + mouth * 0.9, 0.07 + mouth * 1.25, 0, 0, Math.PI * 2);
    stroke('150,100,120', 0.85 * g, 0.16);

    // Gold drop earrings, swaying like pendulums.
    for (const sig of [-1, 1]) {
      ctx.save();
      ctx.translate(sig * 8.4, -22.6);
      ctx.rotate(Math.sin(t * 1.4 + sig) * 0.12 * sw + sig * 0.05);
      poly([[0, 0], [0.5, 1.6], [0, 3.6], [-0.5, 1.6]]); ctx.closePath();
      ctx.fillStyle = `rgba(${PAL.gold},0.9)`; ctx.fill();
      stroke(PAL.gold, 0.9, 0.08);
      ctx.restore();
    }
  }
  requestAnimationFrame(frame);
}
