#!/usr/bin/env python3
"""Analisa um vídeo de referência (link ou ficheiro local) e escreve uma ficha de ritmo para orientar o roteiro.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/referencia.py "https://www.youtube.com/shorts/..."
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/referencia.py URL --section 0-30          # só os primeiros 30 s
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/referencia.py URL --cookies-from-browser chrome   # sites que pedem sessão
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/referencia.py URL --meta-only              # só metadados, sem descarregar
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/referencia.py build/final.mp4 --out-dir build/revisao   # o nosso vídeo, para comparar

Para cada entrada cria referencias/<origem-id>/ (ou --out-dir) com:
  video.mp4          cópia em baixa resolução (720p por omissão), só para estudo
  info.json          metadados úteis (título, canal, duração, visualizações, hashtags, capítulos)
  cortes.csv         instante de cada corte e duração de cada plano
  folha.jpg          um frame do meio de cada plano (até 16), com a zona segura de reel se for vertical
  transcricao.*      fala com tempos por palavra (faster-whisper, local)
  ficha.md / .json   métricas de ritmo: planos, duração média, cortes/10 s, palavras/s, gancho dos 3 s, loudness

O download usa o yt-dlp (pip install yt-dlp; manter atualizado, os sites mudam). Os cookies do browser só são lidos
com --cookies-from-browser e nunca são guardados. Material de terceiros fica nesta pasta e serve só para estudo:
a montagem lê apenas scenes/ e audio/, e nada de referencias/ deve entrar no vídeo final.
"""
import argparse, csv, json, pathlib, re, shutil, statistics, subprocess, sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
KEEP = ['id', 'title', 'uploader', 'channel', 'webpage_url', 'extractor_key', 'duration', 'view_count', 'like_count',
        'comment_count', 'upload_date', 'tags', 'categories', 'width', 'height', 'fps', 'chapters', 'language']


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def ytdlp_cmd():
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        if shutil.which('yt-dlp'):
            return ['yt-dlp']
    sys.exit('[erro] falta o yt-dlp: python3 -m pip install --user yt-dlp')


def slug(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('-')[:60] or 'video'


def download(url, out, a):
    """Descarrega com o yt-dlp; devolve (caminho do vídeo ou None, metadados reduzidos)."""
    base = ytdlp_cmd() + ['--no-playlist', '--no-progress', '--write-info-json', '-o', str(out / 'video.%(ext)s')]
    if a.cookies_from_browser:
        base += ['--cookies-from-browser', a.cookies_from_browser]
    if a.meta_only:
        base += ['--skip-download']
    else:
        h = a.max_height
        base += ['-f', f'bv*[height<={h}][ext=mp4]+ba[ext=m4a]/bv*[height<={h}]+ba/b[height<={h}]/b',
                 '--merge-output-format', 'mp4']
        if a.section:
            base += ['--download-sections', f'*{a.section}', '--force-keyframes-at-cuts']
    r = run(base + [url])
    if r.returncode != 0:
        sys.exit('[erro] yt-dlp falhou:\n' + '\n'.join(r.stderr.strip().splitlines()[-6:]) +
                 '\nSugestões: atualizar (pip install -U yt-dlp); usar --cookies-from-browser <browser> se o site pedir sessão.')
    raw = out / 'video.info.json'
    full = json.loads(raw.read_text()) if raw.exists() else {}
    raw.unlink(missing_ok=True)  # o original traz URLs assinados e cabeçalhos; fica só o essencial
    info = {k: full[k] for k in KEEP if full.get(k) not in (None, [], '')}
    if full.get('description'):
        info['description'] = full['description'][:1500]
    vids = [p for p in out.glob('video.*') if p.suffix in ('.mp4', '.mkv', '.webm', '.mov')]
    return (vids[0] if vids else None), info


def probe(v):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
             '-of', 'json', str(v)])
    j = json.loads(r.stdout or '{}')
    vs = next((s for s in j.get('streams', []) if s.get('codec_type') == 'video'), {})
    num, _, den = vs.get('r_frame_rate', '0/1').partition('/')
    return {'duration': float(j.get('format', {}).get('duration', 0)), 'width': vs.get('width'), 'height': vs.get('height'),
            'fps': round(float(num) / float(den or 1), 3) if float(den or 1) else None,
            'has_audio': any(s.get('codec_type') == 'audio' for s in j.get('streams', []))}


def cuts(v, threshold):
    r = run(['ffmpeg', '-hide_banner', '-i', str(v), '-an', '-vf', f"scale=320:-2,select='gt(scene,{threshold})',showinfo",
             '-f', 'null', '-'])
    ts = [float(m) for m in re.findall(r'pts_time:([0-9.]+)', r.stderr)]
    out = []
    for t in ts:  # dois "cortes" a menos de 0,2 s são a mesma transição
        if t > 0.2 and (not out or t - out[-1] > 0.2):
            out.append(round(t, 3))
    return out


def loudness(v):
    r = run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(v), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
    i = re.findall(r'I:\s+(-?[0-9.]+) LUFS', r.stderr)
    p = re.findall(r'Peak:\s+(-?[0-9.]+) dBFS', r.stderr)
    s = run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(v), '-vn', '-af', 'silencedetect=noise=-40dB:d=0.3',
             '-f', 'null', '-']).stderr
    sil = sum(float(x) for x in re.findall(r'silence_duration: ([0-9.]+)', s))
    return {'lufs': float(i[-1]) if i else None, 'true_peak_dbtp': float(p[-1]) if p else None, 'silencio_s': round(sil, 2)}


def transcribe(v, out, a):
    cmd = [sys.executable, str(SCRIPTS / 'transcribe.py'), str(v), '--out-dir', str(out), '--formats', 'txt,json',
           '--model', a.model]
    if a.language:
        cmd += ['--language', a.language]
    r = run(cmd)
    j = out / (v.stem + '.json')
    if r.returncode != 0 or not j.exists():
        print('[aviso] transcrição falhou: ' + ' '.join(r.stderr.strip().splitlines()[-2:]), file=sys.stderr)
        return None
    for ext in ('json', 'txt'):  # nomes estáveis
        src = out / f'{v.stem}.{ext}'
        if src.exists():
            src.replace(out / f'transcricao.{ext}')
    return json.loads((out / 'transcricao.json').read_text())


def main():
    ap = argparse.ArgumentParser(description='Ficha de ritmo de um vídeo de referência (link ou ficheiro).')
    ap.add_argument('entrada', help='URL (qualquer site suportado pelo yt-dlp) ou caminho de um vídeo local')
    ap.add_argument('--out-dir', default=None, help='pasta de saída (por omissão referencias/<origem-id>)')
    ap.add_argument('--max-height', type=int, default=720, help='altura máxima a descarregar (720)')
    ap.add_argument('--section', help='só um trecho, em segundos ou mm:ss: "0-30", "1:10-1:40"')
    ap.add_argument('--cookies-from-browser', help='chrome | firefox | edge... para sites que pedem sessão (a do próprio utilizador)')
    ap.add_argument('--meta-only', action='store_true', help='só metadados (sem vídeo, sem análise)')
    ap.add_argument('--threshold', type=float, default=0.3, help='sensibilidade da deteção de cortes (0.2 apanha mais, 0.4 menos)')
    ap.add_argument('--no-transcribe', action='store_true')
    ap.add_argument('--model', default='small', help='modelo do faster-whisper (small chega para medir ritmo)')
    ap.add_argument('--language', default=None)
    ap.add_argument('--force', action='store_true', help='voltar a descarregar mesmo que já exista')
    a = ap.parse_args()

    is_url = re.match(r'^[a-z][a-z0-9+.-]*://', a.entrada, re.I) is not None
    if is_url:
        r = run(ytdlp_cmd() + ['--no-playlist', '--print', '%(extractor_key)s-%(id)s'] +
                (['--cookies-from-browser', a.cookies_from_browser] if a.cookies_from_browser else []) + [a.entrada])
        name = slug(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else slug(a.entrada.split('//')[-1])
    else:
        src = pathlib.Path(a.entrada)
        if not a.entrada.strip() or not src.is_file():
            sys.exit(f'[erro] ficheiro não encontrado: {a.entrada!r}')
        name = slug(src.stem)
    out = pathlib.Path(a.out_dir) if a.out_dir else pathlib.Path('referencias') / name
    out.mkdir(parents=True, exist_ok=True)

    info = {}
    if is_url:
        existing = out / 'video.mp4'
        if existing.exists() and not a.force and not a.meta_only:
            video = existing
            info = json.loads((out / 'info.json').read_text()) if (out / 'info.json').exists() else {}
        else:
            video, info = download(a.entrada, out, a)
        (out / 'info.json').write_text(json.dumps(info, ensure_ascii=False, indent=1))
        if a.meta_only:
            print(json.dumps(info, ensure_ascii=False, indent=1)); print(f'\n{out}/info.json'); return
        if not video:
            sys.exit('[erro] o yt-dlp não produziu vídeo')
        if video.suffix != '.mp4':
            mp4 = out / 'video.mp4'
            run(['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-c:v', 'libx264', '-crf', '20', '-c:a', 'aac', str(mp4)])
            video.unlink(); video = mp4
    else:
        video = pathlib.Path(a.entrada)

    p = probe(video)
    D = p['duration']
    if D <= 0 or not p['width']:
        sys.exit(f'[erro] não consegui ler o vídeo: {video}')
    cs = cuts(video, a.threshold)
    bounds = [0.0] + cs + [D]
    shots = [round(b - a_, 3) for a_, b in zip(bounds, bounds[1:]) if b - a_ > 0.01]
    with open(out / 'cortes.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['plano', 'inicio_s', 'fim_s', 'duracao_s'])
        for i, (s, e) in enumerate(zip(bounds, bounds[1:]), 1):
            w.writerow([i, round(s, 3), round(e, 3), round(e - s, 3)])

    # folha: o meio de cada plano (no máximo 16, igualmente escolhidos)
    mids = [(s + e) / 2 for s, e in zip(bounds, bounds[1:])]
    if len(mids) < 6:  # poucos cortes secos (ex. motion graphics com transições animadas): frames espaçados
        mids = [D * (i + 0.5) / 12 for i in range(12)]
    if len(mids) > 16:
        mids = [mids[round(i * (len(mids) - 1) / 15)] for i in range(16)]
    vertical = (p['height'] or 0) > (p['width'] or 0)
    sheet = [sys.executable, str(SCRIPTS / 'contact_sheet.py'), str(video), '--times', ','.join(f'{t:.2f}' for t in mids),
             '--cols', str(8 if len(mids) in (8, 16) else min(6, len(mids))), '--width', '200' if vertical else '320', '--out', str(out / 'folha.jpg')]
    if vertical:
        sheet.append('--safe')
    run(sheet)

    audio = loudness(video) if p['has_audio'] else {}
    tr = None if (a.no_transcribe or not p['has_audio']) else transcribe(video, out, a)
    words = (tr or {}).get('words') or []
    speech = {}
    if words:
        st, en = words[0]['start'], words[-1]['end']
        seg_time = sum(s['end'] - s['start'] for s in tr.get('segments', []))
        hook = [w['word'].strip() for w in words if w['start'] < 3.0]
        speech = {'palavras': len(words), 'idioma': tr.get('language'),
                  'palavras_por_s': round(len(words) / max(en - st, 0.1), 2),
                  'primeira_palavra_s': round(st, 2), 'fala_cobre_pct': round(100 * seg_time / max(D, 0.1)),
                  'gancho_3s': ' '.join(hook)}

    ficha = {'entrada': a.entrada, 'pasta': str(out), 'duracao_s': round(D, 2), 'resolucao': f"{p['width']}x{p['height']}",
             'fps': p['fps'], 'vertical': vertical, 'planos': len(shots), 'cortes': len(cs),
             'plano_medio_s': round(statistics.mean(shots), 2) if shots else None,
             'plano_mediano_s': round(statistics.median(shots), 2) if shots else None,
             'plano_min_s': min(shots) if shots else None, 'plano_max_s': max(shots) if shots else None,
             'cortes_por_10s': round(10 * len(cs) / max(D, 0.1), 2), 'primeiro_corte_s': cs[0] if cs else None,
             'cortes_nos_3s': sum(1 for c in cs if c < 3), 'audio': audio, 'fala': speech,
             'metadados': {k: info.get(k) for k in ('title', 'uploader', 'webpage_url', 'view_count', 'like_count', 'upload_date', 'tags') if info.get(k) is not None}}
    (out / 'ficha.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=1))

    m = ficha['metadados']
    L = [f"# Ficha de referência — {m.get('title') or video.name}", '',
         '> Material de terceiros, só para estudo. Não entra no vídeo final (a montagem lê apenas scenes/ e audio/).' if is_url else '> Vídeo local analisado.', '',
         f"- Origem: {m.get('webpage_url') or a.entrada}" + (f" · {m['uploader']}" if m.get('uploader') else ''),
         f"- Duração {ficha['duracao_s']} s · {ficha['resolucao']} · {ficha['fps']} fps" +
         (f" · {m['view_count']:,} visualizações".replace(',', '.') if m.get('view_count') else ''), '',
         '## Ritmo visual', '',
         f"- {ficha['planos']} planos, {ficha['cortes']} cortes ({ficha['cortes_por_10s']} por 10 s)",
         f"- Plano médio {ficha['plano_medio_s']} s (mediana {ficha['plano_mediano_s']} s; mais curto {ficha['plano_min_s']} s, mais longo {ficha['plano_max_s']} s)",
         f"- Primeiro corte aos {ficha['primeiro_corte_s']} s; {ficha['cortes_nos_3s']} cortes nos primeiros 3 s",
         '- Planos e tempos em cortes.csv; um frame de cada plano em folha.jpg' if len(cs) >= 5 else '- Planos e tempos em cortes.csv; folha.jpg com 12 frames igualmente espaçados', '']
    if len(cs) < 2 and D > 8:
        L[-1:-1] = ['- Atenção: quase nenhum corte seco. Vídeos de motion graphics mudam de cena com transições animadas, que a',
                    '  deteção não distingue do movimento normal; contar as cenas na folha.jpg. Com filmagem, baixar --threshold (0.2).']
    if speech:
        L += ['## Fala', '', f"- {speech['palavras']} palavras ({speech['idioma']}), {speech['palavras_por_s']} palavras/s",
              f"- Primeira palavra aos {speech['primeira_palavra_s']} s; fala ocupa {speech['fala_cobre_pct']} % do vídeo",
              f"- Gancho (0–3 s): “{speech['gancho_3s']}”", '- Texto completo em transcricao.txt', '']
    elif p['has_audio']:
        L += ['## Fala', '', '- Sem fala detetada (ou transcrição desligada).', '']
    if audio:
        L += ['## Áudio', '', f"- Loudness {audio['lufs']} LUFS, pico {audio['true_peak_dbtp']} dBTP, {audio['silencio_s']} s de silêncio", '']
    if m.get('tags'):
        L += ['## Hashtags / tags', '', '- ' + ', '.join(m['tags'][:20]), '']
    L += ['## Como usar no roteiro', '',
          f"- Duração por cena ≈ plano médio ({ficha['plano_medio_s']} s); palavras por cena ≈ duração × {speech.get('palavras_por_s', 2)}",
          '- Copiar a estrutura (gancho, ritmo, onde entra a chamada final), nunca as imagens, a música ou o texto.']
    (out / 'ficha.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L)); print(f'\nFicheiros em {out}/')


if __name__ == '__main__':
    main()
