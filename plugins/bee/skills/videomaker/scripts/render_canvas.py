#!/usr/bin/env python3
"""Renderiza uma cena Canvas (HTML com renderFrame(t), WIDTH, HEIGHT, FPS, DURATION_S)
frame a frame com Chromium headless e produz um MP4 via ffmpeg.
Uso (a partir da raiz do projeto): python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/render_canvas.py scenes/01.html scenes/01.mp4 [dir_frames]
Requer: playwright (Python), Google Chrome, ffmpeg. A cena pode carregar imagens de sources/ por caminho
relativo (ex. ../sources/logos/x.png): o Chrome é lançado com --allow-file-access-from-files para o canvas
não ficar "tainted" e o toDataURL continuar a funcionar.
Com --background video.mp4 a cena é composta por cima de um vídeo (stock) recortado a 9:16 e escurecido
(--dim); a cena deve deixar o canvas transparente (não pintar o fundo) onde o vídeo deve aparecer.
"""
import argparse, base64, pathlib, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('scene'); ap.add_argument('out'); ap.add_argument('frames_dir', nargs='?')
ap.add_argument('--background', help='vídeo de fundo (ex. stock/pixabay-123.mp4): a cena é composta por cima; deixar o canvas transparente onde o vídeo deve aparecer')
ap.add_argument('--dim', type=float, default=0.55, help='fator de luminosidade do vídeo de fundo (0..1), para o texto ler bem')
ap.add_argument('--bg-offset', type=float, default=0.0, help='segundos a saltar no início do vídeo de fundo')
ap.add_argument('--crf', type=int, default=18, help='qualidade x264 da cena (menor = melhor); 18 por omissão porque a montagem volta a codificar')
a = ap.parse_args()
src, out = pathlib.Path(a.scene).resolve(), pathlib.Path(a.out).resolve()
frames_dir = pathlib.Path(a.frames_dir) if a.frames_dir else pathlib.Path(tempfile.mkdtemp())
frames_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--allow-file-access-from-files"])
    page = browser.new_page()
    page.goto(src.as_uri())
    page.wait_for_function("typeof renderFrame === 'function'")
    fps, dur, w, h = page.evaluate("[FPS, DURATION_S, WIDTH, HEIGHT]")
    n = round(fps * dur)
    # Parar o loop de pré-visualização para não competir com o render determinístico
    page.evaluate("window.requestAnimationFrame = () => 0")
    for i in range(n):
        t = i / fps
        data = page.evaluate(
            "t => { renderFrame(t); return document.getElementById('c').toDataURL('image/png'); }", t)
        (frames_dir / f"{i:05d}.png").write_bytes(base64.b64decode(data.split(",", 1)[1]))
    browser.close()

if a.background:
    # vídeo recortado ao centro para WxH, escurecido, em loop se for curto; PNGs (alpha) por cima
    vf = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},"
          f"lutyuv=y=val*{a.dim},setpts=PTS-STARTPTS[bg];[bg][1:v]overlay=format=auto:shortest=1,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a.bg_offset), "-stream_loop", "-1", "-i", a.background,
                    "-framerate", str(fps), "-i", str(frames_dir / "%05d.png"),
                    "-filter_complex", vf, "-map", "[v]", "-t", str(dur),
                    "-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-r", str(fps), str(out)], check=True)
else:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", str(frames_dir / "%05d.png"),
                    "-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-r", str(fps), str(out)], check=True)
print(f"{out.name}: {n} frames, {w}x{h} @ {fps} fps, {dur} s")
