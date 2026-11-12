// icons.js — desenha ícones Lucide no Canvas a partir de sources/icons/lucide/icons.js (gerado por scripts/icons.py).
// Incluir nas cenas: <script src="../sources/icons/lucide/icons.js"></script> e depois este ficheiro
// (copiado para scenes/ ou referenciado por caminho). Tudo determinístico; o traço "escreve-se" com setLineDash.
window.Icons = (() => {
  const cache = {};
  const paths = name => {
    if (!window.LUCIDE || !window.LUCIDE[name]) throw new Error(`ícone "${name}" não está em icons.js — correr scripts/icons.py ${name}`);
    return cache[name] || (cache[name] = window.LUCIDE[name].map(d => new Path2D(d)));
  };
  // Comprimento aproximado de um caminho (amostragem) para o setLineDash do efeito "a escrever-se"
  const lengths = {};
  function length(name) {
    if (lengths[name]) return lengths[name];
    const c = document.createElement('canvas').getContext('2d'); let total = 0;
    for (const d of window.LUCIDE[name]) {
      // estimativa: soma das distâncias entre os números do caminho (suficiente para animar)
      const nums = d.match(/-?\d*\.?\d+/g).map(Number); let x = 0, y = 0, first = true;
      for (let i = 0; i + 1 < nums.length; i += 2) { if (!first) total += Math.hypot(nums[i] - x, nums[i + 1] - y); x = nums[i]; y = nums[i + 1]; first = false; }
    }
    return lengths[name] = Math.max(24, total * 0.6);
  }
  /**
   * draw(ctx, name, cx, cy, size, opts)
   *  size: lado do ícone em px (o viewBox 24 é escalado); opts: color, lineWidth (em unidades do viewBox, Lucide=2),
   *  alpha, rot, scale, progress (0..1 = traço a escrever-se), fill (preenche em vez de traçar), bg/bgRadius (tile atrás).
   */
  function draw(ctx, name, cx, cy, size, { color = '#111111', lineWidth = 2, alpha = 1, rot = 0, scale = 1, progress = 1, fill = false, bg = null, bgRadius = 0.22, bgPad = 0.5 } = {}) {
    if (alpha <= 0 || scale <= 0 || progress <= 0) return;
    const s = size / 24;
    ctx.save(); ctx.globalAlpha = alpha; ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(scale, scale);
    if (bg) { const half = size * (0.5 + bgPad), r = size * (1 + 2 * bgPad) * bgRadius; ctx.fillStyle = bg; ctx.beginPath(); ctx.roundRect(-half, -half, 2 * half, 2 * half, r); ctx.fill(); }
    ctx.scale(s, s); ctx.translate(-12, -12);
    ctx.lineWidth = lineWidth; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = color; ctx.fillStyle = color;
    if (progress < 1) { const L = length(name); ctx.setLineDash([L * progress, L + 1]); }
    for (const p of paths(name)) fill ? ctx.fill(p) : ctx.stroke(p);
    ctx.restore();
  }
  return { draw, length, paths };
})();
