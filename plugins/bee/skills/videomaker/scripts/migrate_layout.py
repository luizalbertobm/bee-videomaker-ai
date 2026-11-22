#!/usr/bin/env python3
"""Migra um projeto do layout antigo do videomaker (tudo na raiz) para a estrutura por vídeo.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/migrate_layout.py                     # só mostra o plano
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/migrate_layout.py --slug reel-lancamento --apply
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/migrate_layout.py --json              # plano em JSON (para o /bee:organize)

Layout antigo → novo:
  sources/logos, fonts, icons e outras subpastas      → brand/…
  sources/identidade-visual.md (ou na raiz)           → brand/brand-guide.md
  sources/<áudio, vídeo ou imagem solto>              → videos/<slug>/production/inputs/
  stock/sfx/ → library/sfx/ · stock/ → library/stock/ · musica*.mp3 → library/music/
  creditos.md → library/credits.md (e uma cópia em videos/<slug>/deliverables/credits.md)
  referencias/ → references/
  scenes/ audio/ build/ → videos/<slug>/production/…   legendas.srt → production/subtitles.srt
  roteiro*.md → videos/<slug>/script*.md              *.mp4 / *.webm da raiz → videos/<slug>/deliverables/
Todos os projetos antigos são tratados como um só vídeo (<slug>); versões e variantes ficam dentro dele.

Nos .html/.js/.css movidos, os caminhos relativos que apontavam para algo que mudou de sítio (ex. ../sources/logos/x.svg)
são reescritos para o novo sítio. Nunca sobrescreve: um destino já ocupado fica por migrar e é listado, tal como tudo o
que o script não reconhece (pastas próprias do utilizador, repositórios, .env, .claude). Regista o que fez em
.videomaker/migration.log. Só biblioteca padrão.
"""
import argparse, datetime, json, os, pathlib, re, shutil, sys, unicodedata

MEDIA = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.mp4', '.mov', '.webm', '.mkv',
         '.png', '.jpg', '.jpeg', '.webp', '.gif'}
TEXT_REWRITE = {'.html', '.htm', '.js', '.css'}
IGNORE = {'.git', '.env', '.claude', '.videomaker', '.gitignore', '.venv', 'venv', 'node_modules', '__pycache__',
          'brand', 'library', 'references', 'videos', 'README.md', 'CLAUDE.md'}


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def plan(root, slug):
    """Lista de (origem, destino, regra); e lista do que fica por migrar."""
    V = pathlib.Path('videos') / slug
    P = V / 'production'
    moves, left = [], []

    def mv(src, dst, why): moves.append((pathlib.Path(src).relative_to(root), pathlib.Path(dst), why))

    for e in sorted(root.iterdir(), key=lambda p: p.name):
        n = e.name
        if n in IGNORE: continue
        if n == 'sources' and e.is_dir():
            for s in sorted(e.iterdir(), key=lambda p: p.name):
                if s.is_dir(): mv(s, pathlib.Path('brand') / s.name, 'marca')
                elif s.name == 'identidade-visual.md': mv(s, 'brand/brand-guide.md', 'guia da marca')
                elif s.suffix.lower() in MEDIA: mv(s, P / 'inputs' / s.name, 'material do vídeo')
                else: mv(s, pathlib.Path('brand') / s.name, 'marca')
        elif n == 'identidade-visual.md': mv(e, 'brand/brand-guide.md', 'guia da marca')
        elif n == 'stock' and e.is_dir():
            for s in sorted(e.iterdir(), key=lambda p: p.name):
                if s.name == 'sfx' and s.is_dir(): mv(s, 'library/sfx', 'efeitos do projeto')
                else: mv(s, pathlib.Path('library/stock') / s.name, 'stock')
        elif n == 'referencias' and e.is_dir(): mv(e, 'references', 'referências')
        elif n in ('scenes', 'audio', 'build') and e.is_dir(): mv(e, P / n, 'produção')
        elif n == 'legendas.srt': mv(e, P / 'subtitles.srt', 'produção')
        elif n == 'sfx.tsv': mv(e, P / 'sfx.tsv', 'produção')
        elif n == 'creditos.md': mv(e, 'library/credits.md', 'créditos')
        elif e.is_file() and re.match(r'musica.*\.(mp3|wav|m4a|ogg)$', n, re.I): mv(e, pathlib.Path('library/music') / n, 'música')
        elif e.is_file() and re.match(r'roteiro.*\.md$', n, re.I): mv(e, V / re.sub(r'^roteiro', 'script', n, flags=re.I), 'roteiro')
        elif e.is_file() and e.suffix.lower() in ('.mp4', '.webm', '.mov'): mv(e, V / 'deliverables' / n, 'entrega')
        else: left.append(e)
    return moves, left


def is_empty_dir(p): return p.is_dir() and not any(p.iterdir())


def remap_factory(root, moves):
    table = sorted(((root / s).resolve(), (root / d).resolve()) for s, d, _ in moves)
    table.sort(key=lambda t: -len(str(t[0])))
    def remap(abs_old):
        for s, d in table:
            if abs_old == s or s in abs_old.parents:
                return d / abs_old.relative_to(s)
        return abs_old
    return remap


REF = re.compile(r'''(?P<q>['"(])(?P<p>(?:\.\./|\./)+[^'"()\s]+)''')


def rewrite_refs(new_file, old_file, remap):
    """Reescreve caminhos relativos num ficheiro de texto que mudou de pasta."""
    try: txt = new_file.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError): return 0
    count = 0
    def sub(m):
        nonlocal count
        rel = m.group('p')
        target = remap(pathlib.Path(os.path.normpath(old_file.parent / rel)))
        new_rel = os.path.relpath(target, new_file.parent).replace(os.sep, '/')
        if not new_rel.startswith('.'): new_rel = './' + new_rel if rel.startswith('./') else new_rel
        if new_rel == rel: return m.group(0)
        count += 1
        return m.group('q') + new_rel
    out = REF.sub(sub, txt)
    if count: new_file.write_text(out, encoding='utf-8')
    return count


def main():
    ap = argparse.ArgumentParser(description='Migra um projeto do videomaker para a estrutura por vídeo.')
    ap.add_argument('--slug', help='nome do vídeo (por omissão AAAA-MM-<nome da pasta do projeto>)')
    ap.add_argument('--apply', action='store_true', help='mover de facto (sem isto só mostra o plano)')
    ap.add_argument('--json', action='store_true', help='plano em JSON')
    a = ap.parse_args()
    root = pathlib.Path.cwd().resolve()

    slug = slugify(a.slug or root.name) or 'video'
    if not re.match(r'^\d{4}-\d{2}-', slug): slug = f'{datetime.date.today():%Y-%m}-{slug}'
    moves, left = plan(root, slug)

    # destinos ocupados (uma pasta vazia, ex. criada pelo new_video.sh ou pelo doctor, não conta)
    rows = []
    for s, d, why in moves:
        dst = root / d
        conflict = dst.exists() and not is_empty_dir(dst)
        rows.append({'from': str(s), 'to': str(d), 'rule': why, 'conflict': conflict})
    ok = [r for r in rows if not r['conflict']]
    conflicts = [r for r in rows if r['conflict']]
    old_layout = any((root / x).exists() for x in ('sources', 'scenes', 'audio'))

    if a.json and not a.apply:
        print(json.dumps({'project': str(root), 'slug': slug, 'video_dir': f'videos/{slug}', 'old_layout': old_layout,
                          'moves': rows, 'left_in_place': [str(p.name) for p in left]}, ensure_ascii=False, indent=1))
        return
    if not moves:
        print('Nada a migrar: o projeto não tem o layout antigo (sources/, scenes/, audio/ na raiz).'); return

    w = max(len(r['from']) for r in rows)
    print(f'Vídeo: videos/{slug}/\n')
    for r in rows:
        print(f"  {r['from']:<{w}}  →  {r['to']}{'   [destino ocupado: fica por migrar]' if r['conflict'] else ''}")
    if left:
        print('\nFica onde está (não reconhecido; mover à mão se fizer parte de um vídeo):')
        for p in left: print(f"  {p.name}{'/' if p.is_dir() else ''}")
    if not a.apply:
        print('\nNada foi movido. Para aplicar: --apply' + ('' if a.slug else ' (e --slug <nome> para escolher o nome do vídeo)'))
        return

    remap = remap_factory(root, [(r['from'], r['to'], r['rule']) for r in ok])
    log, rewritten = [], 0
    for r in ok:
        src, dst = root / r['from'], root / r['to']
        if is_empty_dir(dst): dst.rmdir()
        dst.parent.mkdir(parents=True, exist_ok=True)
        files = [src] if src.is_file() else [f for f in src.rglob('*') if f.is_file()]
        shutil.move(str(src), str(dst))
        for old in files:
            if old.suffix.lower() in TEXT_REWRITE:
                new = dst if old == src else dst / old.relative_to(src)
                rewritten += rewrite_refs(new, old, remap)
        log.append(r)

    V = root / 'videos' / slug
    for sub in ('production/inputs', 'production/scenes', 'production/audio', 'production/build', 'deliverables'):
        (V / sub).mkdir(parents=True, exist_ok=True)
    gi = V / 'production/build/.gitignore'
    if not gi.exists(): gi.write_text('*\n')
    for sub in ('brand/logos', 'brand/fonts', 'library/stock', 'library/sfx', 'library/music'):
        (root / sub).mkdir(parents=True, exist_ok=True)
    cred, dcred = root / 'library/credits.md', V / 'deliverables/credits.md'
    if cred.exists() and not dcred.exists(): shutil.copy2(cred, dcred)

    (root / '.videomaker').mkdir(exist_ok=True)
    gi = root / '.videomaker/.gitignore'
    if not gi.exists(): gi.write_text('*\n')
    with open(root / '.videomaker/migration.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'date': datetime.datetime.now().isoformat(timespec='seconds'), 'slug': slug,
                            'moves': log, 'conflicts': conflicts, 'left_in_place': [p.name for p in left]},
                           ensure_ascii=False) + '\n')
    print(f'\nMovidos {len(log)} itens; {rewritten} caminhos reescritos em cenas; registo em .videomaker/migration.log.')
    if conflicts: print(f'{len(conflicts)} itens ficaram por migrar porque o destino já existe.')


if __name__ == '__main__':
    main()
