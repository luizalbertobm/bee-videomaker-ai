#!/usr/bin/env python3
"""Folha de contacto: grelha de frames-chave numa só imagem, para rever uma animação ou escolher stock sem abrir vídeos.
Só ffmpeg/ffprobe e a biblioteca padrão (sem Pillow).

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py scenes/03.mp4                 # 8 frames, 4 colunas
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py scenes/03.mp4 --frames 12 --cols 6
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py scenes/03.mp4 --times 0,0.4,1.25,2.9  # instantes exatos
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py scenes/0*.mp4 --frames 5         # uma linha por cena
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py stock/thumbs/*.jpg --cols 6      # imagens soltas, uma por célula

Os frames de cada vídeo vão do primeiro ao último, igualmente espaçados; cada célula leva o nome do ficheiro e o
instante em segundos, para cruzar com o código da cena (renderFrame(t)). Saída por omissão: <primeiro>_folha.png
(ou --out). Ler a imagem resultante em vez de abrir o vídeo: apanha textos fora das caixas, elementos cortados,
frames vazios e saltos entre cenas.
"""
import argparse, json, pathlib, shutil, subprocess, sys, tempfile

IMG_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}


def probe(path):
    """(largura, altura, duração, fps) do primeiro stream de vídeo."""
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(path)],
                       capture_output=True, text=True)
    if r.returncode: sys.exit(f'[erro] ffprobe não leu {path}: {r.stderr.strip()}')
    d = json.loads(r.stdout); s = d['streams'][0]
    num, den = (s.get('r_frame_rate') or '30/1').split('/')
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return s['width'], s['height'], float(d.get('format', {}).get('duration') or 0), fps


def esc(text):
    """Escapar texto para o drawtext do ffmpeg."""
    return text.replace('\\', '\\\\').replace("'", "’").replace(':', '\\:').replace('%', '\\%')


def grab(src, t, dest, w, h, label, use_label):
    """Um frame de src no instante t (None = imagem), encaixado em w x h sem deformar.
    Imagens compõem-se sobre cinzento médio, para as transparências de PNG (logos pretos ou brancos) se lerem;
    vídeos não têm alfa e levam só barras escuras (a composição com uma fonte de cor perdia frames após o -ss)."""
    fit = f'scale={w}:{h}:force_original_aspect_ratio=decrease'
    if t is None:
        fc = (f'color=c=0x808080:s={w}x{h}:d=1[bg];[0:v]{fit},format=rgba[fg];'
              f'[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1')
    else:
        fc = f'[0:v]{fit},pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x202020'
    if use_label and label:
        fs = max(12, w // 18)
        fc += (f",drawtext=text='{esc(label)}':font=Sans:fontsize={fs}:fontcolor=white:"
               f"box=1:boxcolor=black@0.65:boxborderw={fs // 3}:x={fs // 2}:y=h-th-{fs // 2}")
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if t is not None: cmd += ['-ss', f'{t:.3f}']
    cmd += ['-i', str(src), '-filter_complex', fc + '[out]', '-map', '[out]', '-frames:v', '1', str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and dest.exists(), r.stderr.strip()


def main():
    ap = argparse.ArgumentParser(description='Folha de contacto de vídeos ou imagens (só ffmpeg).')
    ap.add_argument('inputs', nargs='+', help='vídeos (mp4, webm…) e/ou imagens')
    ap.add_argument('--frames', type=int, default=8, help='frames por vídeo (8 por omissão)')
    ap.add_argument('--times', help='instantes exatos em segundos, separados por vírgulas (substitui --frames)')
    ap.add_argument('--cols', type=int, help='colunas (por omissão 4 para um vídeo; com vários vídeos, uma linha por vídeo)')
    ap.add_argument('--width', type=int, default=320, help='largura de cada célula em px (320)')
    ap.add_argument('--out', help='ficheiro de saída .png ou .jpg')
    ap.add_argument('--no-labels', action='store_true', help='sem nome e instante em cada célula')
    a = ap.parse_args()
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): sys.exit('[erro] precisa de ffmpeg e ffprobe')

    srcs = [pathlib.Path(p) for p in a.inputs]
    for p in srcs:
        if not p.exists(): sys.exit(f'[erro] não existe: {p}')
    videos = [p for p in srcs if p.suffix.lower() not in IMG_EXT]
    times_fixed = [float(x) for x in a.times.split(',')] if a.times else None

    # célula com a proporção do primeiro ficheiro (os outros entram com barras, sem deformar)
    w0, h0, _, _ = probe(srcs[0])
    cw = a.width - a.width % 2; ch = round(cw * h0 / w0); ch -= ch % 2

    # lista de células: (ficheiro, instante ou None, rótulo)
    cells, per_row = [], None
    multi = len(srcs) > 1
    for p in srcs:
        if p.suffix.lower() in IMG_EXT:
            cells.append((p, None, p.name)); continue
        _, _, dur, fps = probe(p)
        last = max(0.0, dur - 1.5 / fps)       # dentro do último frame (o fim do ficheiro já não tem imagem)
        if times_fixed:
            ts = [min(t, last) for t in times_fixed if t <= dur + 1e-6]
        else:
            n = max(1, a.frames)
            ts = [last * i / (n - 1) for i in range(n)] if n > 1 else [0.0]
        for t in ts:
            cells.append((p, t, f'{p.name}  {t:.2f} s' if multi else f'{t:.2f} s'))
        per_row = len(ts) if per_row is None else per_row
    if not cells: sys.exit('[erro] nenhum instante dentro da duração dos vídeos')

    cols = a.cols or (per_row if len(videos) > 1 and len(videos) == len(srcs) else min(4, len(cells)))
    rows = -(-len(cells) // cols)
    out = pathlib.Path(a.out) if a.out else srcs[0].with_name(srcs[0].stem + '_folha.png')

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp); use_label = not a.no_labels; warned = False
        for k, (src, t, label) in enumerate(cells):
            dest = tmp / f'{k:04d}.png'
            ok, err = grab(src, t, dest, cw, ch, label, use_label)
            if not ok and t is not None and t > 0:   # instante no limite do ficheiro: recuar meio frame
                ok, err = grab(src, max(0.0, t - 0.5 / 30), dest, cw, ch, label, use_label)
            if not ok and use_label and ('drawtext' in err or 'font' in err.lower()):   # ffmpeg sem freetype/fontconfig
                use_label = False
                if not warned: print('[aviso] ffmpeg sem drawtext utilizável; folha sem rótulos', file=sys.stderr); warned = True
                ok, err = grab(src, t, dest, cw, ch, label, False)
            if not ok: sys.exit(f'[erro] frame {t if t is not None else ""} de {src}: {err or "o ffmpeg não devolveu imagem"}')
        for k in range(len(cells), rows * cols):  # completar a última linha
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=0x202020:s={cw}x{ch}',
                            '-frames:v', '1', str(tmp / f'{k:04d}.png')], check=True)
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-i', str(tmp / '%04d.png'),
                            '-vf', f'tile={cols}x{rows}:padding=6:margin=6:color=0x101010', '-frames:v', '1', str(out)],
                           capture_output=True, text=True)
        if r.returncode: sys.exit(f'[erro] montagem da grelha: {r.stderr.strip()}')
    W = cols * cw + (cols - 1) * 6 + 12; H = rows * ch + (rows - 1) * 6 + 12
    print(f'{out}: {len(cells)} frames, {cols}x{rows}, {W}x{H} px')


if __name__ == '__main__':
    main()
