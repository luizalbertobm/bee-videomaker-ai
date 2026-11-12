#!/usr/bin/env python3
"""Pesquisa e descarrega imagens, vídeos e sons gratuitos de bancos com API (Pexels, Pixabay, Openverse),
e regista os créditos. Só biblioteca padrão; sem dependências.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "honeycomb macro" --type video --orientation portrait
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "office team" --type image --source pixabay --limit 10
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "whoosh" --type audio                      # só Openverse/Freesound
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "city night" --type video --download 1,3 --out-dir stock
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "bee" --type image --json                 # saída JSON p/ automação

Chaves (gratuitas) por variável de ambiente ou ficheiro .env na raiz do projeto:
  PEXELS_API_KEY   https://www.pexels.com/api/        200 pedidos/h, 20.000/mês
  PIXABAY_API_KEY  https://pixabay.com/api/docs/      100 pedidos/min; respostas cacheadas 24 h (exigência do Pixabay)
  Openverse não precisa de chave (limite anónimo baixo); só imagens e áudio, filtrado para uso comercial.

Cada download acrescenta uma linha a creditos.md (fonte, autor, licença, link). Pexels e Pixabay pedem que se
mostre a origem; Openverse devolve a atribuição exata exigida pela licença CC — copiar para a descrição do vídeo.
"""
import argparse, hashlib, json, os, pathlib, sys, time, urllib.parse, urllib.request

UA = 'videomaker-skill/1.0 (+local tool)'
CACHE = pathlib.Path.home() / '.cache' / 'videomaker' / 'stock'
CACHE_TTL = 24 * 3600


def load_env():
    p = pathlib.Path('.env')
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def get_json(url, headers=None):
    """GET com cache de 24 h em disco (exigido pelo Pixabay; poupa quota no Pexels)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1((url + json.dumps(headers or {}, sort_keys=True)).encode()).hexdigest()
    cf = CACHE / f'{key}.json'
    if cf.exists() and time.time() - cf.stat().st_mtime < CACHE_TTL:
        return json.loads(cf.read_text())
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json', **(headers or {})})
    for attempt in range(3):   # o Openverse devolve 502/504 com alguma frequência; repetir com espera
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            hint = {401: 'chave inválida ou em falta', 403: 'acesso recusado (chave/limite)', 429: 'limite de pedidos excedido; esperar'}.get(e.code, '')
            raise SystemExit(f'[erro] HTTP {e.code} em {url.split("?")[0]} {hint}')
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2: time.sleep(2 * (attempt + 1)); continue
            raise SystemExit(f'[erro] rede: {e} em {url.split("?")[0]}')
    cf.write_text(json.dumps(data))
    return data


# ---------- fontes ----------
ORIENT = {'portrait': {'pexels': 'portrait', 'pixabay': 'vertical', 'openverse': 'tall'},
          'landscape': {'pexels': 'landscape', 'pixabay': 'horizontal', 'openverse': 'wide'},
          'square': {'pexels': 'square', 'pixabay': 'all', 'openverse': 'square'}}


def search_pexels(q, kind, orient, limit):
    key = os.environ.get('PEXELS_API_KEY')
    if not key: return [], 'PEXELS_API_KEY não definida'
    if kind == 'audio': return [], 'Pexels não tem áudio'
    base = 'https://api.pexels.com/videos/search' if kind == 'video' else 'https://api.pexels.com/v1/search'
    params = {'query': q, 'per_page': limit, 'size': 'large'}
    if orient: params['orientation'] = ORIENT[orient]['pexels']
    d = get_json(base + '?' + urllib.parse.urlencode(params), {'Authorization': key})
    out = []
    for it in d.get('videos' if kind == 'video' else 'photos', []):
        if kind == 'video':
            files = [f for f in it.get('video_files', []) if f.get('file_type') == 'video/mp4' and f.get('width')]
            best = max(files, key=lambda f: f['width'] * f['height']) if files else None
            if not best: continue
            out.append(dict(source='pexels', id=str(it['id']), kind='video', width=best['width'], height=best['height'],
                            duration=it.get('duration'), author=it['user']['name'], author_url=it['user'].get('url'),
                            page=it['url'], download=best['link'], ext='mp4', license='Pexels License', title=''))
        else:
            out.append(dict(source='pexels', id=str(it['id']), kind='image', width=it['width'], height=it['height'],
                            duration=None, author=it['photographer'], author_url=it.get('photographer_url'),
                            page=it['url'], download=it['src']['original'], ext='jpg', license='Pexels License', title=it.get('alt', '')))
    return out, None


def search_pixabay(q, kind, orient, limit):
    key = os.environ.get('PIXABAY_API_KEY')
    if not key: return [], 'PIXABAY_API_KEY não definida'
    if kind == 'audio': return [], 'a API do Pixabay não cobre áudio'
    base = 'https://pixabay.com/api/videos/' if kind == 'video' else 'https://pixabay.com/api/'
    params = {'key': key, 'q': q, 'per_page': max(3, min(limit, 200)), 'safesearch': 'true'}
    if kind == 'image': params['image_type'] = 'photo'; params['min_width'] = 1280
    if orient: params['orientation'] = ORIENT[orient]['pixabay']
    d = get_json(base + '?' + urllib.parse.urlencode(params))
    out = []
    for it in d.get('hits', []):
        if kind == 'video':
            v = it['videos']; best = next((v[s] for s in ('large', 'medium', 'small') if v.get(s, {}).get('url')), None)
            if not best: continue
            out.append(dict(source='pixabay', id=str(it['id']), kind='video', width=best['width'], height=best['height'],
                            duration=it.get('duration'), author=it['user'], author_url=f"https://pixabay.com/users/{it['user']}-{it['user_id']}/",
                            page=it['pageURL'], download=best['url'], ext='mp4', license='Pixabay Content License', title=it.get('tags', '')))
        else:
            url = it.get('fullHDURL') or it.get('largeImageURL')
            out.append(dict(source='pixabay', id=str(it['id']), kind='image', width=it['imageWidth'], height=it['imageHeight'],
                            duration=None, author=it['user'], author_url=f"https://pixabay.com/users/{it['user']}-{it['user_id']}/",
                            page=it['pageURL'], download=url, ext='jpg', license='Pixabay Content License', title=it.get('tags', '')))
    return out, None


def cc_label(lic, ver):
    lic = (lic or '').lower()
    if lic == 'cc0': return f'CC0 {ver}'.strip()
    if lic == 'pdm': return 'Public Domain Mark'
    return f'CC {lic.upper()} {ver}'.strip()


def search_openverse(q, kind, orient, limit):
    if kind == 'video': return [], 'Openverse não tem vídeo'
    base = f'https://api.openverse.org/v1/{"audio" if kind == "audio" else "images"}/'
    params = {'q': q, 'page_size': min(limit, 50), 'license_type': 'commercial', 'mature': 'false'}
    if kind == 'image' and orient: params['aspect_ratio'] = ORIENT[orient]['openverse']
    try:
        d = get_json(base + '?' + urllib.parse.urlencode(params))
    except SystemExit as e:
        return [], str(e)
    out = []
    for it in d.get('results', []):
        ext = (it.get('filetype') or ('mp3' if kind == 'audio' else 'jpg')).lower()
        out.append(dict(source=f"openverse/{it.get('source', '')}", id=it['id'], kind=kind, width=it.get('width'), height=it.get('height'),
                        duration=(it.get('duration') or 0) / 1000 if kind == 'audio' else None, author=it.get('creator') or '',
                        author_url=it.get('creator_url'), page=it.get('foreign_landing_url'), download=it.get('url'), ext=ext,
                        license=cc_label(it.get('license', ''), it.get('license_version', '')),
                        title=it.get('title') or '', attribution=it.get('attribution')))
    return out, None


SOURCES = {'pexels': search_pexels, 'pixabay': search_pixabay, 'openverse': search_openverse}


# ---------- download e créditos ----------
def download(item, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{item['source'].split('/')[0]}-{item['id']}.{item['ext']}"
    dest = out_dir / name
    req = urllib.request.Request(item['download'], headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
        while chunk := r.read(1 << 16): f.write(chunk)
    return dest


def credit_line(item, dest):
    attr = item.get('attribution') or f"{item['title'] or item['kind']} por {item['author']} ({item['license']})"
    return f"| `{dest}` | {item['source']} | {item['author']} | {item['license']} | [página]({item['page']}) | {attr.strip()} |\n"


def append_credits(path, lines):
    header = '# Créditos de assets de stock\n\n| Ficheiro | Fonte | Autor | Licença | Link | Atribuição |\n|---|---|---|---|---|---|\n'
    if not path.exists(): path.write_text(header)
    with open(path, 'a') as f: f.writelines(lines)


def main():
    ap = argparse.ArgumentParser(description='Stock gratuito: Pexels, Pixabay, Openverse.')
    ap.add_argument('query')
    ap.add_argument('--type', default='image', choices=['image', 'video', 'audio'])
    ap.add_argument('--source', default='auto', help='auto | pexels | pixabay | openverse | lista separada por vírgulas')
    ap.add_argument('--orientation', default=None, choices=['portrait', 'landscape', 'square'])
    ap.add_argument('--limit', type=int, default=8, help='resultados por fonte')
    ap.add_argument('--min-width', type=int, default=0)
    ap.add_argument('--min-height', type=int, default=0)
    ap.add_argument('--download', default=None, help='números dos resultados a descarregar, ex. 1,3 ou all')
    ap.add_argument('--out-dir', default='stock')
    ap.add_argument('--credits', default='creditos.md')
    ap.add_argument('--json', action='store_true', help='imprimir resultados em JSON (sem tabela)')
    a = ap.parse_args()
    load_env()

    order = {'image': ['pexels', 'pixabay', 'openverse'], 'video': ['pexels', 'pixabay'], 'audio': ['openverse']}[a.type]
    sources = order if a.source == 'auto' else [s.strip() for s in a.source.split(',')]
    results, notes = [], []
    for s in sources:
        if s not in SOURCES: notes.append(f'{s}: fonte desconhecida'); continue
        items, note = SOURCES[s](a.query, a.type, a.orientation, a.limit)
        if note: notes.append(f'{s}: {note}')
        results += [i for i in items if (i.get('width') or 0) >= a.min_width and (i.get('height') or 0) >= a.min_height]

    if a.json:
        print(json.dumps({'results': results, 'notes': notes}, ensure_ascii=False, indent=1))
    else:
        for n in notes: print(f'[nota] {n}', file=sys.stderr)
        if not results: print('Sem resultados.'); return
        print(f'{"#":>2}  {"fonte":18} {"dim/dur":14} {"autor":22} {"licença":24} página')
        for k, it in enumerate(results, 1):
            dim = f"{it['width']}x{it['height']}" if it.get('width') else ''
            if it.get('duration'): dim += f" {it['duration']:.0f}s"
            print(f'{k:>2}  {it["source"][:18]:18} {dim:14} {(it["author"] or "")[:22]:22} {it["license"][:24]:24} {it["page"]}')

    if a.download:
        picks = range(1, len(results) + 1) if a.download == 'all' else [int(x) for x in a.download.split(',')]
        lines = []
        for k in picks:
            it = results[k - 1]; dest = download(it, pathlib.Path(a.out_dir)); lines.append(credit_line(it, dest))
            print(f'descarregado {k}: {dest} ({dest.stat().st_size // 1024} KB)', file=sys.stderr)
        append_credits(pathlib.Path(a.credits), lines)
        print(f'créditos acrescentados a {a.credits}', file=sys.stderr)


if __name__ == '__main__':
    main()
