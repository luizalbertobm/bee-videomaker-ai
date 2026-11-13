// devices.js — mockups de dispositivos em perspetiva (portátil e telemóvel) só com Canvas 2D, com uma página a
// fazer scroll no ecrã. Sem dependências: incluir nas cenas com <script src="devices.js"></script> (copiado para
// scenes/ ou referenciado por caminho). Tudo determinístico em função dos argumentos; nada guarda estado entre frames.
//
//   const k = Devices.laptop(ctx, pagina, pose, { scroll, url, theme, glow });
//   const k = Devices.phone(ctx, pagina, pose, { scroll, theme, glow });
//
// pagina: Image (captura de scripts/capture_site.py) ou canvas (interface desenhada pela cena, ou
//         Devices.placeholderPage() enquanto não há captura). scroll em px da página; Devices.maxScroll() dá o limite.
// pose:   { cx, cy, s, yaw, pitch, roll, tilt } — posição no canvas (portátil: dobradiça; telemóvel: centro), px por
//         unidade do modelo, rotação para os lados (yaw < 0 aproxima o lado direito), inclinação da câmara, rotação no
//         plano da imagem e, no portátil, abertura da tampa para trás. Devices.POSES traz poses prontas para 1080x1920;
//         Devices.mix(A, B, p) interpola entre duas (movimento de câmara) e Devices.float(P, T) dá uma flutuação lenta.
// Devolve os cantos do dispositivo (tl, tr, bl, br) e at(u, v): ponto do canvas que corresponde a (u, v) do ecrã
// (0..1), para pousar selos, cursores ou realces por cima.
window.Devices = (() => {
  const TAU = Math.PI * 2, FONT = 'system-ui, "DejaVu Sans", Arial, sans-serif';
  const lerp = (a, b, p) => a + (b - a) * p;
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  const rr = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); };
  const path = (ctx, pts) => { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); };
  const lin = (ctx, p, q, stops) => { const g = ctx.createLinearGradient(p[0], p[1], q[0], q[1]); stops.forEach(([o, c]) => g.addColorStop(o, c)); return g; };
  function glowAt(ctx, cx, cy, r, c, a) {
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r); g.addColorStop(0, rgba(c, a)); g.addColorStop(1, rgba(c, 0));
    ctx.fillStyle = g; ctx.fillRect(cx - r, cy - r, 2 * r, 2 * r);
  }

  // ---------- Temas: cor do corpo, do aro e do brilho. Passar o nome ou um objeto com as chaves a mudar ----------
  const THEMES = {
    graphite: { top: ['#1d1f25', '#5a5f6b'], side: '#3a3e47', well: '#0b0c0f', key: '#1c1e24', front: ['#8a8f9b', '#3a3e47'], notch: 'rgba(0,0,0,0.4)', lid: '#07080a', rim: 'rgba(132,138,150,0.95)', glow: [150, 170, 255], shadow: 'rgba(0,0,0,0.6)' },
    silver: { top: ['#8f96a3', '#e9ecf1'], side: '#9aa1ad', well: '#17181c', key: '#2a2d34', front: ['#ffffff', '#aab0bb'], notch: 'rgba(90,96,108,0.55)', lid: '#0b0c0f', rim: 'rgba(228,232,238,0.95)', glow: [150, 180, 255], shadow: 'rgba(0,0,0,0.5)' },
    violet: { top: ['#34255c', '#a590da'], side: '#5a4690', well: '#120a1e', key: '#2a1e40', front: ['#f4edff', '#927bc8'], notch: 'rgba(60,40,100,0.55)', lid: '#0b0812', rim: 'rgba(206,188,246,0.9)', glow: [206, 96, 255], shadow: 'rgba(4,0,14,0.7)' },
  };
  const themeOf = t => typeof t === 'string' ? (THEMES[t] || THEMES.graphite) : { ...THEMES.graphite, ...t };
  // Barra do browser do portátil: 'dark', 'light', 'violet' ou { bg, pill, fg, off }
  const CHROME = {
    dark: { bg: '#1e1f25', pill: '#30323b', fg: 'rgba(255,255,255,0.9)', off: 'rgba(255,255,255,0.38)' },
    light: { bg: '#eef0f3', pill: '#ffffff', fg: '#3c4043', off: 'rgba(60,64,67,0.35)' },
    violet: { bg: '#1b1526', pill: '#2d2440', fg: 'rgba(255,255,255,0.9)', off: 'rgba(255,255,255,0.38)' },
  };

  // ---------- Poses prontas para um canvas 1080x1920 (noutro formato, ajustar cx, cy e s) ----------
  const POSES = {
    laptop: {
      side: { cx: 950, cy: 1470, s: 64, yaw: -0.46, pitch: 0.20, tilt: 0.20, roll: 0 },   // a sair pela direita, texto à esquerda
      hero: { cx: 566, cy: 1450, s: 55, yaw: -0.20, pitch: 0.17, tilt: 0.19, roll: 0 },   // inteiro, ligeiramente de lado
      front: { cx: 540, cy: 1400, s: 56, yaw: 0, pitch: 0.12, tilt: 0.16, roll: 0 },      // de frente
    },
    phone: {
      side: { cx: 800, cy: 1160, s: 66, yaw: -0.50, pitch: 0.10, roll: -0.07 },           // à direita, texto à esquerda
      hero: { cx: 560, cy: 1120, s: 60, yaw: -0.30, pitch: 0.08, roll: 0.05 },            // centrado, ligeiramente rodado
      front: { cx: 540, cy: 1080, s: 62, yaw: 0, pitch: 0, roll: 0 },                     // de frente
    },
  };
  const mix = (A, B, p) => { const o = {}; for (const k of new Set([...Object.keys(A), ...Object.keys(B)])) o[k] = lerp(A[k] || 0, B[k] || 0, p); return o; };
  // Flutuação lenta; T deve ser o tempo global do vídeo (início da cena + t) para não saltar nos cortes
  const float = (P, T, k = 1) => ({ ...P, cy: P.cy + 7 * k * Math.sin(T * 1.1), yaw: (P.yaw || 0) + 0.018 * k * Math.sin(T * 0.8 + 1), pitch: (P.pitch || 0) + 0.008 * k * Math.sin(T * 0.9) });

  // Projeção: modelo (x direita, y cima, z para o observador) -> canvas, com perspetiva simples
  function projector(P, foc = 44) {
    const cy = Math.cos(P.yaw || 0), sy = Math.sin(P.yaw || 0), cp = Math.cos(P.pitch || 0), sp = Math.sin(P.pitch || 0), cr = Math.cos(P.roll || 0), sr = Math.sin(P.roll || 0);
    return (x, y, z) => {
      const x1 = x * cy + z * sy, z1 = -x * sy + z * cy, y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp, k = foc / (foc - z2), X = x1 * k, Y = y2 * k;
      return [P.cx + (X * cr - Y * sr) * P.s, P.cy - (X * sr + Y * cr) * P.s];
    };
  }

  // ---------- Ecrã: canvas auxiliar com a janela visível da página (e a barra do browser ou de estado) ----------
  const screens = {};
  const screen = (kind, w, h) => screens[kind] || (screens[kind] = Object.assign(document.createElement('canvas'), { width: w, height: h }));
  const SIZE = { laptop: [1520, 950, 74], phone: [780, 1650, 124] };   // largura, altura e barra superior do ecrã, em px
  const dims = page => [page.naturalWidth || page.width, page.naturalHeight || page.height];
  // Scroll máximo (px da página) para a página não acabar antes do fundo do ecrã
  function maxScroll(kind, page, { bar = true } = {}) {
    const [w, h, b] = SIZE[kind], [pw, ph] = dims(page); return Math.max(0, ph - (h - (bar ? b : 0)) * pw / w);
  }
  function drawPage(s, page, x, y, w, h, scroll, pageBg) {
    const [pw, ph] = dims(page), k = w / pw, vis = h / k, sy = Math.max(0, Math.min(ph - vis, scroll)), sh = Math.min(vis, ph - sy);
    s.fillStyle = pageBg; s.fillRect(x, y, w, h); s.imageSmoothingQuality = 'high';
    s.drawImage(page, 0, sy, pw, sh, x, y, w, sh * k);
  }
  function browserBar(s, W, bar, url, ch, font) {
    const m = bar / 2; s.fillStyle = ch.bg; s.fillRect(0, 0, W, bar); s.lineWidth = 3; s.lineCap = 'round'; s.lineJoin = 'round';
    const chev = (x, d, col) => { s.strokeStyle = col; s.beginPath(); s.moveTo(x + 6 * d, m - 10); s.lineTo(x - 5 * d, m); s.lineTo(x + 6 * d, m + 10); s.stroke(); };
    chev(46, 1, ch.fg); chev(108, -1, ch.off);
    s.strokeStyle = s.fillStyle = ch.fg; s.beginPath(); s.arc(170, m, 10, 0.9, TAU - 0.35); s.stroke();
    const ex = 170 + 10 * Math.cos(-0.35), ey = m + 10 * Math.sin(-0.35); s.beginPath(); s.moveTo(ex + 6, ey - 8); s.lineTo(ex + 5, ey + 4); s.lineTo(ex - 6, ey - 1); s.closePath(); s.fill();
    s.fillStyle = ch.pill; rr(s, 214, 13, Math.min(820, W - 254), bar - 26, (bar - 26) / 2); s.fill();
    s.strokeStyle = s.fillStyle = ch.fg; s.lineWidth = 2.5; rr(s, 238, m - 3, 16, 13, 3); s.fill(); s.beginPath(); s.arc(246, m - 3, 5, Math.PI, TAU); s.stroke();
    s.font = `400 25px ${font}`; s.textAlign = 'left'; s.textBaseline = 'middle'; s.fillText(url, 268, m + 1);
  }
  function statusBar(s, W, bar, time, fg, bg, font) {
    const m = bar / 2 + 7; s.fillStyle = bg; s.fillRect(0, 0, W, bar);
    s.fillStyle = s.strokeStyle = fg; s.font = `600 34px ${font}`; s.textAlign = 'left'; s.textBaseline = 'middle'; s.fillText(time, 62, m + 1);
    for (let i = 0; i < 4; i++) { rr(s, W - 222 + i * 13, m + 13 - (9 + i * 6), 8, 9 + i * 6, 2); s.fill(); }      // rede
    s.lineWidth = 2.5; rr(s, W - 140, m - 14, 56, 28, 8); s.stroke(); rr(s, W - 135, m - 9, 40, 18, 4); s.fill(); rr(s, W - 81, m - 5, 4, 10, 2); s.fill();   // bateria
  }

  // ---------- Deformação: desenha src pela malha de triângulos afins definida por map(u, v) -> [x, y] ----------
  // O Canvas 2D só faz transformações afins; com células pequenas o conjunto lê-se como perspetiva.
  function tri(ctx, src, s0, s1, s2, d0, d1, d2, bx, by, bw, bh) {
    const den = s0[0] * (s1[1] - s2[1]) + s1[0] * (s2[1] - s0[1]) + s2[0] * (s0[1] - s1[1]);
    const co = i => [(d0[i] * (s1[1] - s2[1]) + d1[i] * (s2[1] - s0[1]) + d2[i] * (s0[1] - s1[1])) / den,
      (d0[i] * (s2[0] - s1[0]) + d1[i] * (s0[0] - s2[0]) + d2[i] * (s1[0] - s0[0])) / den,
      (d0[i] * (s1[0] * s2[1] - s2[0] * s1[1]) + d1[i] * (s2[0] * s0[1] - s0[0] * s2[1]) + d2[i] * (s0[0] * s1[1] - s1[0] * s0[1])) / den];
    const [a, c, e] = co(0), [b, d, f] = co(1), mx = (d0[0] + d1[0] + d2[0]) / 3, my = (d0[1] + d1[1] + d2[1]) / 3;
    const ex = p => { const dx = p[0] - mx, dy = p[1] - my, l = Math.hypot(dx, dy) || 1; return [p[0] + dx / l * 0.9, p[1] + dy / l * 0.9]; };   // sobrepõe 1 px para não ficarem costuras
    const q0 = ex(d0), q1 = ex(d1), q2 = ex(d2);
    ctx.save(); ctx.beginPath(); ctx.moveTo(q0[0], q0[1]); ctx.lineTo(q1[0], q1[1]); ctx.lineTo(q2[0], q2[1]); ctx.closePath(); ctx.clip();
    ctx.transform(a, b, c, d, e, f);
    const x0 = Math.max(0, bx - 2), y0 = Math.max(0, by - 2), x1 = Math.min(src.width, bx + bw + 2), y1 = Math.min(src.height, by + bh + 2);
    ctx.drawImage(src, x0, y0, x1 - x0, y1 - y0, x0, y0, x1 - x0, y1 - y0); ctx.restore();
  }
  function warp(ctx, src, map, nx = 16, ny = 10) {
    const pts = []; for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) pts.push(map(i / nx, j / ny));
    const P = (i, j) => pts[j * (nx + 1) + i], cw = src.width / nx, ch = src.height / ny;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const x0 = i * cw, y0 = j * ch, x1 = x0 + cw, y1 = y0 + ch;
      tri(ctx, src, [x0, y0], [x1, y0], [x0, y1], P(i, j), P(i + 1, j), P(i, j + 1), x0, y0, cw, ch);
      tri(ctx, src, [x1, y1], [x0, y1], [x1, y0], P(i + 1, j + 1), P(i, j + 1), P(i + 1, j), x0, y0, cw, ch);
    }
  }

  // ---------- Portátil. Modelo com 16 unidades de largura; dobradiça no eixo x, tampa de 10,5 e base de 10,6 ----------
  // opções: scroll (px da página), url, bar (false = sem barra de browser), chrome ('dark' | 'light' | 'violet' | objeto),
  //         theme ('graphite' | 'silver' | 'violet' | objeto), glow (0..1, brilho à volta), pageBg (cor de fundo da página)
  function laptop(ctx, page, P, { scroll = 0, url = 'sualoja.com.br', bar = true, chrome = 'dark', theme = 'graphite', glow = 1, pageBg = '#ffffff', font = FONT, mesh = [16, 10] } = {}) {
    const th = themeOf(theme), ch = typeof chrome === 'string' ? (CHROME[chrome] || CHROME.dark) : { ...CHROME.dark, ...chrome };
    const pr = projector(P), ct = Math.cos(P.tilt || 0), st = Math.sin(P.tilt || 0), sy_ = Math.sin(P.yaw || 0), u = P.s, Dp = 10.6, TH = 0.34;
    const lid = (x, h) => pr(x, h * ct, -h * st), base = (x, d, y = 0) => pr(x, y, d);
    const quad = pts => path(ctx, pts);
    ctx.save(); ctx.lineJoin = 'round';
    // brilho no chão e sombra de contacto
    if (glow > 0) { const gc = base(0, Dp * 0.62, -TH); ctx.save(); ctx.translate(gc[0], gc[1] + 0.6 * u); ctx.scale(1, 0.26); glowAt(ctx, 0, 0, 12 * u, th.glow, 0.62 * glow); ctx.restore(); }
    ctx.save(); ctx.shadowColor = th.shadow; ctx.shadowBlur = 0.9 * u; ctx.shadowOffsetY = 0.35 * u; ctx.fillStyle = th.lid; quad([base(-7.9, 0.2, -TH), base(7.9, 0.2, -TH), base(7.9, Dp, -TH), base(-7.9, Dp, -TH)]); ctx.fill(); ctx.restore();
    // base: face lateral visível, tampo, teclado, trackpad e face frontal
    const side = x => { ctx.fillStyle = th.side; quad([base(x, 0), base(x, Dp), base(x, Dp, -TH), base(x, 0, -TH)]); ctx.fill(); };
    if (sy_ < 0) side(8); else if (sy_ > 0) side(-8);
    ctx.fillStyle = ctx.strokeStyle = lin(ctx, base(0, 0), base(0, Dp), [[0, th.top[0]], [1, th.top[1]]]); ctx.lineWidth = 0.12 * u; quad([base(-8, 0), base(8, 0), base(8, Dp), base(-8, Dp)]); ctx.fill(); ctx.stroke();
    ctx.fillStyle = th.well; quad([base(-7.25, 0.85), base(7.25, 0.85), base(7.25, 6.25), base(-7.25, 6.25)]); ctx.fill();
    const rows = 5, cols = 14, kx0 = -7.05, kx1 = 7.05, kd0 = 1.05, kd1 = 6.05, kw = (kx1 - kx0) / cols, kh = (kd1 - kd0) / rows, gp = 0.09;
    const key = (c0, c1, r) => { quad([base(kx0 + c0 * kw + gp, kd0 + r * kh + gp), base(kx0 + c1 * kw - gp, kd0 + r * kh + gp), base(kx0 + c1 * kw - gp, kd0 + (r + 1) * kh - gp), base(kx0 + c0 * kw + gp, kd0 + (r + 1) * kh - gp)]); ctx.fill(); };
    ctx.fillStyle = th.key;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { if (r === rows - 1 && c > 3 && c < 10) { if (c === 4) key(4, 10, r); continue; } key(c, c + 1, r); }   // barra de espaço = 6 teclas
    ctx.fillStyle = 'rgba(255,255,255,0.07)'; ctx.strokeStyle = 'rgba(255,255,255,0.22)'; ctx.lineWidth = 1.5; quad([base(-2.7, 6.9), base(2.7, 6.9), base(2.7, 10.1), base(-2.7, 10.1)]); ctx.fill(); ctx.stroke();
    ctx.fillStyle = lin(ctx, base(0, Dp), base(0, Dp, -TH), [[0, th.front[0]], [1, th.front[1]]]); quad([base(-8, Dp), base(8, Dp), base(8, Dp, -TH), base(-8, Dp, -TH)]); ctx.fill();
    ctx.fillStyle = th.notch; quad([base(-1.3, Dp), base(1.3, Dp), base(1.1, Dp, -TH * 0.45), base(-1.1, Dp, -TH * 0.45)]); ctx.fill();
    // tampa: halo, aresta metálica, moldura, ecrã deformado e reflexo
    const L = [lid(-8, 0), lid(8, 0), lid(8, 10.5), lid(-8, 10.5)];
    ctx.save(); if (glow > 0) { ctx.shadowColor = rgba(th.glow, 0.6 * glow); ctx.shadowBlur = 1.6 * u; } ctx.fillStyle = th.lid; quad(L); ctx.fill(); ctx.restore();
    ctx.strokeStyle = th.rim; ctx.lineWidth = 0.42 * u + 4; quad(L); ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle = th.lid; ctx.lineWidth = 0.42 * u; quad(L); ctx.stroke(); ctx.fill();
    const [SW, SH, B] = SIZE.laptop, bh = bar ? B : 0, scr = screen('laptop', SW, SH), sctx = scr.getContext('2d');
    drawPage(sctx, page, 0, bh, SW, SH - bh, scroll, pageBg); if (bar) browserBar(sctx, SW, bh, url, ch, font);
    const S = (a, b) => lid(-7.6 + 15.2 * a, 10.05 - 9.5 * b), Q = v => [S(0, 0), S(1, 0), S(1, v), S(0, v)];
    // fundo do ecrã na cor da página e da barra: as arestas dos triângulos misturam-se com isto e não com a moldura escura
    ctx.fillStyle = pageBg; quad(Q(1)); ctx.fill(); if (bar) { ctx.fillStyle = ch.bg; quad(Q(bh / SH)); ctx.fill(); }
    ctx.imageSmoothingQuality = 'high'; warp(ctx, scr, S, mesh[0], mesh[1]);
    ctx.fillStyle = lin(ctx, S(0, 0), S(0.55, 1), [[0, 'rgba(255,255,255,0.10)'], [0.5, 'rgba(255,255,255,0.02)'], [1, 'rgba(255,255,255,0)']]); quad(Q(1)); ctx.fill();
    const cam = lid(0, 10.28); ctx.fillStyle = th.key; ctx.beginPath(); ctx.arc(cam[0], cam[1], 0.07 * u, 0, TAU); ctx.fill();
    ctx.restore();
    return { tl: L[3], tr: L[2], bl: L[0], br: L[1], at: S };
  }

  // ---------- Telemóvel. Corpo de 7,4 x 15,2 unidades, centrado na pose; ecrã 7,0 x 14,8 com cantos redondos ----------
  // opções: scroll, theme, glow, pageBg, status ('dark' = texto escuro, 'light' = texto claro, false = sem barra de estado),
  //         statusBg (cor da barra de estado; por omissão pageBg), island (ilha da câmara), home (traço inferior), time
  const rrPts = (w, h, r, n = 7) => { const p = [], hw = w / 2 - r, hh = h / 2 - r;
    [[hw, hh], [-hw, hh], [-hw, -hh], [hw, -hh]].forEach(([cx, cy], q) => { for (let i = 0; i <= n; i++) { const a = (q + i / n) * Math.PI / 2; p.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } });
    return p; };
  function phone(ctx, page, P, { scroll = 0, theme = 'graphite', glow = 1, pageBg = '#ffffff', status = 'dark', statusBg = null, island = true, home = true, time = '9:41', font = FONT, mesh = [10, 20] } = {}) {
    const th = themeOf(theme), pr = projector(P), u = P.s, BW = 7.4, BH = 15.2, BR = 1.3, TH = 0.8, SWu = 7.0, SHu = 14.8, SR = 1.1;
    const poly = (w, h, r, z, oy = 0) => rrPts(w, h, r).map(([x, y]) => pr(x, y + oy, z));
    ctx.save(); ctx.lineJoin = 'round';
    if (glow > 0) { const c = pr(0, 0, -TH); glowAt(ctx, c[0], c[1], 12 * u, th.glow, 0.40 * glow); }
    // corpo: fatias empilhadas de trás para a frente dão a espessura e a aresta metálica em qualquer ângulo
    const N = 10;
    for (let i = 0; i <= N; i++) { const z = -TH * (1 - i / N), k = i / N;
      ctx.save(); if (i === 0) { ctx.shadowColor = th.shadow; ctx.shadowBlur = 1.5 * u; ctx.shadowOffsetY = 0.7 * u; }
      ctx.fillStyle = lin(ctx, pr(-BW / 2, 0, z), pr(BW / 2, 0, z), [[0, th.front[1]], [0.18 + 0.2 * k, th.front[0]], [0.6, th.front[1]], [1, th.front[0]]]);
      path(ctx, poly(BW, BH, BR, z)); ctx.fill(); ctx.restore(); }
    ctx.fillStyle = th.lid; path(ctx, poly(BW - 0.14, BH - 0.14, BR - 0.07, 0)); ctx.fill();
    // ecrã: página (com barra de estado) deformada e recortada pelos cantos redondos
    const [SW, SH, B] = SIZE.phone, bh = status ? B : 0, scr = screen('phone', SW, SH), sctx = scr.getContext('2d'), fg = status === 'light' ? '#ffffff' : '#111111';
    drawPage(sctx, page, 0, bh, SW, SH - bh, scroll, pageBg); if (status) statusBar(sctx, SW, bh, time, fg, statusBg || pageBg, font);
    const S = (a, b) => pr(-SWu / 2 + SWu * a, SHu / 2 - SHu * b, 0), edge = poly(SWu, SHu, SR, 0);
    ctx.save(); path(ctx, edge); ctx.fillStyle = pageBg; ctx.fill(); ctx.clip();
    ctx.imageSmoothingQuality = 'high'; warp(ctx, scr, S, mesh[0], mesh[1]);
    ctx.fillStyle = lin(ctx, S(0, 0), S(0.9, 0.6), [[0, 'rgba(255,255,255,0.10)'], [0.5, 'rgba(255,255,255,0.02)'], [1, 'rgba(255,255,255,0)']]); path(ctx, edge); ctx.fill();
    ctx.restore();
    if (island) { ctx.fillStyle = '#000000'; path(ctx, poly(2.2, 0.58, 0.29, 0, SHu / 2 - 0.62)); ctx.fill(); }
    if (home) { ctx.fillStyle = status === 'light' ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.6)'; path(ctx, poly(2.5, 0.1, 0.05, 0, -SHu / 2 + 0.26)); ctx.fill(); }
    ctx.restore();
    return { tl: pr(-BW / 2, BH / 2, 0), tr: pr(BW / 2, BH / 2, 0), bl: pr(-BW / 2, -BH / 2, 0), br: pr(BW / 2, -BH / 2, 0), at: S };
  }

  // ---------- Página de exemplo: loja genérica desenhada em canvas, para ensaiar a cena antes de haver captura ----------
  // kind: 'desktop' (1920 px de largura) ou 'mobile' (780 px). Trocar por uma captura real de scripts/capture_site.py.
  const pages = {};
  function placeholderPage(kind = 'desktop', { accent = '#5b5bd6', name = 'Loja Exemplo', font = FONT } = {}) {
    const id = `${kind}|${accent}|${name}`; if (pages[id]) return pages[id];
    const mob = kind === 'mobile', W = mob ? 780 : 1920, cols = mob ? 2 : 4, rows = mob ? 5 : 4, mx = mob ? 32 : 80, gap = mob ? 24 : 40;
    const nav = mob ? 120 : 110, hero = mob ? 500 : 530, gy = nav + hero + (mob ? 140 : 160), cw = (W - 2 * mx - (cols - 1) * gap) / cols, chh = mob ? 500 : 560, foot = 110;
    const H = gy + rows * (chh + gap) + foot, c = Object.assign(document.createElement('canvas'), { width: W, height: H }), x = c.getContext('2d');
    const t = (s, px, py, size, weight, color, align = 'left') => { x.font = `${weight} ${size}px ${font}`; x.fillStyle = color; x.textAlign = align; x.textBaseline = 'middle'; x.fillText(s, px, py); };
    x.fillStyle = '#ffffff'; x.fillRect(0, 0, W, H);
    // navegação
    x.fillStyle = '#e8eaee'; x.fillRect(0, nav - 2, W, 2);
    if (mob) { x.fillStyle = '#222'; [0, 1, 2].forEach(i => { rr(x, 36, nav / 2 - 14 + i * 12, 40, 4, 2); x.fill(); }); t(name, W / 2, nav / 2, 36, 700, '#16181d', 'center'); }
    else { x.fillStyle = accent; rr(x, mx, nav / 2 - 22, 44, 44, 12); x.fill(); t(name, mx + 62, nav / 2 + 1, 34, 700, '#16181d');
      ['Início', 'Produtos', 'Ofertas', 'Contato'].forEach((s, i) => t(s, 620 + i * 150, nav / 2 + 1, 24, i === 1 ? 700 : 500, i === 1 ? accent : '#4a4f5a'));
      x.fillStyle = '#f1f3f6'; rr(x, 1230, nav / 2 - 26, 400, 52, 26); x.fill(); t('Buscar produtos', 1262, nav / 2 + 1, 22, 400, '#8a8f9b'); }
    x.fillStyle = '#f1f3f6'; x.beginPath(); x.arc(W - mx - 26, nav / 2, 26, 0, TAU); x.fill(); x.fillStyle = accent; x.beginPath(); x.arc(W - mx - 8, nav / 2 - 18, 10, 0, TAU); x.fill();
    // destaque
    const hg = x.createLinearGradient(0, nav, W, nav + hero); hg.addColorStop(0, accent); hg.addColorStop(1, '#16181d'); x.fillStyle = hg; x.fillRect(0, nav, W, hero);
    x.fillStyle = 'rgba(255,255,255,0.12)'; x.beginPath(); x.arc(W - (mob ? 90 : 420), nav + hero * 0.55, mob ? 210 : 300, 0, TAU); x.fill();
    t('Novidades', mx + (mob ? 8 : 40), nav + hero * 0.30, mob ? 60 : 84, 700, '#ffffff'); t('da semana', mx + (mob ? 8 : 40), nav + hero * 0.30 + (mob ? 70 : 96), mob ? 60 : 84, 700, '#ffffff');
    x.fillStyle = '#ffffff'; rr(x, mx + (mob ? 8 : 40), nav + hero * 0.70, mob ? 260 : 300, mob ? 72 : 78, 39); x.fill(); t('Ver produtos', mx + (mob ? 138 : 190), nav + hero * 0.70 + (mob ? 37 : 40), mob ? 26 : 28, 700, '#16181d', 'center');
    // grelha de produtos
    t('Todos os produtos', mx, nav + hero + (mob ? 72 : 84), mob ? 40 : 46, 700, '#16181d'); t(`${cols * rows} itens`, W - mx, nav + hero + (mob ? 74 : 86), mob ? 24 : 26, 400, '#8a8f9b', 'right');
    for (let i = 0; i < cols * rows; i++) {
      const cx = mx + (i % cols) * (cw + gap), cy = gy + Math.floor(i / cols) * (chh + gap), hue = (i * 47 + 210) % 360, ih = chh * 0.58;
      x.fillStyle = '#ffffff'; x.strokeStyle = '#e8eaee'; x.lineWidth = 2; rr(x, cx, cy, cw, chh, 22); x.fill(); x.stroke();
      x.fillStyle = `hsl(${hue},60%,93%)`; rr(x, cx + 12, cy + 12, cw - 24, ih, 14); x.fill();
      x.fillStyle = `hsl(${hue},48%,62%)`; rr(x, cx + cw / 2 - cw * 0.14, cy + 12 + ih * 0.22, cw * 0.28, ih * 0.62, 18); x.fill();
      x.fillStyle = `hsl(${hue},48%,48%)`; rr(x, cx + cw / 2 - cw * 0.08, cy + 12 + ih * 0.13, cw * 0.16, ih * 0.11, 8); x.fill();
      const ty = cy + ih + 54; t(`Produto ${String(i + 1).padStart(2, '0')}`, cx + 22, ty, mob ? 26 : 27, 600, '#16181d');
      t(`R$ ${49 + i * 8},90`, cx + 22, ty + 46, mob ? 30 : 32, 700, '#16181d');
      x.fillStyle = accent; rr(x, cx + 22, cy + chh - 76, cw - 44, 54, 27); x.fill(); t('Adicionar', cx + cw / 2, cy + chh - 48, 23, 700, '#ffffff', 'center');
    }
    x.fillStyle = '#16181d'; x.fillRect(0, H - foot, W, foot); t(name, mx, H - foot / 2, 26, 700, '#ffffff'); t('Página de exemplo', W - mx, H - foot / 2, 22, 400, 'rgba(255,255,255,0.6)', 'right');
    return pages[id] = c;
  }

  return { laptop, phone, POSES, THEMES, CHROME, SIZE, mix, float, maxScroll, warp, placeholderPage };
})();
