#!/usr/bin/env python3
"""Ícones Lucide (ISC, traço 2 px em base 24) para as animações Canvas.
Descarrega SVGs por nome do CDN (unpkg, versão fixa), guarda-os em sources/icons/lucide/ com a cor pedida
e gera sources/icons/lucide/icons.js: cada ícone vira uma lista de caminhos (Path2D) no viewBox 24x24,
para o Canvas desenhar com traço que se escreve (setLineDash), em qualquer cor e tamanho.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/icons.py store message-circle credit-card truck megaphone
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/icons.py --search delivery          # procura por nome e tags
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/icons.py truck --color "#1a1a1a"      # SVG com essa cor (p/ <img>)
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/icons.py --js                        # só regenerar icons.js

Catálogo: https://lucide.dev/icons/ . Sem dependências além da biblioteca padrão.
"""
import argparse, json, math, pathlib, re, sys, urllib.request, xml.etree.ElementTree as ET

VERSION = '1.72.0'
CDN = f'https://unpkg.com/lucide-static@{VERSION}'
OUT = pathlib.Path('sources/icons/lucide')
UA = 'video-pipeline-skill/1.0'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def tags():
    """Nome → tags, do próprio pacote (cache local)."""
    cache = OUT / 'tags.json'
    if not cache.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        cache.write_text(fetch(f'{CDN}/tags.json'))
    return json.loads(cache.read_text())


def arc_path(cx, cy, r):
    return f'M{cx - r},{cy} a{r},{r} 0 1,0 {2 * r},0 a{r},{r} 0 1,0 {-2 * r},0'


def to_paths(svg_text):
    """Elementos SVG (path, circle, line, rect, polyline, polygon, ellipse) → lista de strings 'd'."""
    root = ET.fromstring(svg_text)
    ds = []
    for el in root.iter():
        tag = el.tag.split('}')[-1]; a = el.attrib; f = lambda k, d='0': float(a.get(k, d))
        if tag == 'path': ds.append(a['d'])
        elif tag == 'circle': ds.append(arc_path(f('cx'), f('cy'), f('r')))
        elif tag == 'ellipse':
            cx, cy, rx, ry = f('cx'), f('cy'), f('rx'), f('ry')
            ds.append(f'M{cx - rx},{cy} a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 {-2 * rx},0')
        elif tag == 'line': ds.append(f"M{f('x1')},{f('y1')} L{f('x2')},{f('y2')}")
        elif tag == 'rect':
            x, y, w, h, rx = f('x'), f('y'), f('width'), f('height'), f('rx', a.get('ry', '0'))
            if rx:
                ds.append(f'M{x + rx},{y} h{w - 2 * rx} a{rx},{rx} 0 0 1 {rx},{rx} v{h - 2 * rx} a{rx},{rx} 0 0 1 {-rx},{rx} h{-(w - 2 * rx)} a{rx},{rx} 0 0 1 {-rx},{-rx} v{-(h - 2 * rx)} a{rx},{rx} 0 0 1 {rx},{-rx} z')
            else: ds.append(f'M{x},{y} h{w} v{h} h{-w} z')
        elif tag in ('polyline', 'polygon'):
            pts = re.findall(r'-?\d*\.?\d+', a['points']); pairs = list(zip(pts[0::2], pts[1::2]))
            d = 'M' + ' L'.join(f'{x},{y}' for x, y in pairs); ds.append(d + (' z' if tag == 'polygon' else ''))
    return ds


def write_js():
    icons = {}
    for f in sorted(OUT.glob('*.svg')):
        try: icons[f.stem] = to_paths(f.read_text())
        except Exception as e: print(f'[aviso] {f.name}: {e}', file=sys.stderr)
    js = OUT / 'icons.js'
    js.write_text('// Gerado por ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/icons.py — ícones Lucide v' + VERSION +
                  ' (ISC) como caminhos no viewBox 24x24.\n' +
                  'window.LUCIDE = ' + json.dumps(icons, separators=(',', ':')) + ';\n')
    return js, len(icons)


def main():
    ap = argparse.ArgumentParser(description='Ícones Lucide para animações Canvas.')
    ap.add_argument('names', nargs='*', help='nomes Lucide (ex. truck, shopping-bag, message-circle)')
    ap.add_argument('--search', help='procurar por palavra nos nomes e tags')
    ap.add_argument('--color', default='currentColor', help='cor do traço gravada no SVG (para carregar como <img>)')
    ap.add_argument('--stroke-width', default=None, help='espessura do traço no SVG (Lucide: 2)')
    ap.add_argument('--js', action='store_true', help='regenerar icons.js a partir dos SVGs já descarregados')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if a.search:
        q = a.search.lower(); t = tags()
        hits = [n for n, tg in t.items() if q in n or any(q in x for x in tg)]
        print('\n'.join(hits[:60]) or 'sem resultados'); print(f'({len(hits)} resultados; catálogo com {len(t)} ícones)')
        if not a.names and not a.js: return

    for n in a.names:
        try: svg = fetch(f'{CDN}/icons/{n}.svg')
        except Exception as e: print(f'[erro] {n}: {e} — ver nomes em https://lucide.dev/icons/', file=sys.stderr); continue
        svg = svg.replace('stroke="currentColor"', f'stroke="{a.color}"')
        if a.stroke_width: svg = re.sub(r'stroke-width="[^"]*"', f'stroke-width="{a.stroke_width}"', svg)
        (OUT / f'{n}.svg').write_text(svg); print(f'{n}.svg ok')

    if a.names or a.js:
        js, k = write_js(); print(f'{js}: {k} ícones')


if __name__ == '__main__':
    main()
