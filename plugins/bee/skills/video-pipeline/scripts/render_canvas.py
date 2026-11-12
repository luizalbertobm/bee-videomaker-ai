#!/usr/bin/env python3
"""Renderiza uma cena Canvas (HTML com renderFrame(t), WIDTH, HEIGHT, FPS, DURATION_S)
frame a frame com Chromium headless e produz um MP4 via ffmpeg.
Uso (a partir da raiz do projeto): python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/render_canvas.py scenes/01.html scenes/01.mp4 [dir_frames]
Requer: playwright (Python), Google Chrome, ffmpeg. A cena pode carregar imagens de sources/ por caminho
relativo (ex. ../sources/logos/x.png): o Chrome é lançado com --allow-file-access-from-files para o canvas
não ficar "tainted" e o toDataURL continuar a funcionar.
"""
import base64, pathlib, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

src, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
frames_dir = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else pathlib.Path(tempfile.mkdtemp())
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

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                "-i", str(frames_dir / "%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), str(out)], check=True)
print(f"{out.name}: {n} frames, {w}x{h} @ {fps} fps, {dur} s")
