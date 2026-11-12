#!/usr/bin/env python3
"""Monta uma faixa de efeitos sonoros (WAV) a partir de uma folha de deixas, para a montagem misturar com SFX=.
Uso (raiz do projeto): python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/sfx_track.py deixas.tsv sfx.wav --duration 25 [--dir stock/sfx]

Folha de deixas: uma linha por som, colunas separadas por espaços; "#" inicia comentário.
    tempo_s  som  pico_dB  [pitch]  [inicio_s]  [duracao_s]
  tempo_s    instante do vídeo em que o som começa (o silêncio inicial do ficheiro é cortado, o ataque cai aí)
  som        nome do som, sem extensão (ex. pop): procura-se primeiro em --dir (sons próprios do projeto) e depois na
             biblioteca da skill, assets/sfx/, incluindo subpastas (os nove sons base whoosh, swish, riser, click, tick, pop,
             pop-soft, glock, shimmer e o pacote Kenney "Interface Sounds" em kenney-interface/: click_001, confirmation_002,
             maximize_005, drop_003…; ver CREDITOS.md lá). Pode levar a subpasta (kenney-interface/select_001) para desambiguar.
             --list mostra os sons disponíveis, por pasta
  pico_dB    nível de pico depois de normalizar (ex. -18); cada som é normalizado, por isso o valor é absoluto
  pitch      fator de altura/velocidade (1 = original; 1.26 = terça maior acima; <1 mais grave e lento)
  inicio_s, duracao_s   fatia do ficheiro a usar (para sons longos), com fades curtos nas pontas
Requer ffmpeg e numpy. Tudo determinístico: a mesma folha dá sempre a mesma faixa.
"""
import argparse, pathlib, subprocess, sys, wave
import numpy as np

SR = 44100
ap = argparse.ArgumentParser()
ap.add_argument('cues', nargs='?'); ap.add_argument('out', nargs='?')
ap.add_argument('--duration', type=float, help='duração da faixa (s), igual à do vídeo')
ap.add_argument('--dir', default='stock/sfx', help='pasta de sons do projeto, vista antes da biblioteca da skill')
ap.add_argument('--list', action='store_true', help='listar os sons disponíveis e sair')
a = ap.parse_args()
LIB = pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'sfx'    # biblioteca local da skill
DIRS = [pathlib.Path(a.dir), LIB]
AUDIO_EXT = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aif', '.aiff'}
if a.list:
    for d in DIRS:
        folders = [d] + sorted(x for x in d.rglob('*') if x.is_dir()) if d.is_dir() else []
        if not folders: print(f'{d}: (não existe)'); continue
        for folder in folders:
            names = sorted(f.stem for f in folder.iterdir() if f.suffix.lower() in AUDIO_EXT)
            if names or folder == d: print(f"{folder}: {', '.join(names) or '(vazio)'}")
    sys.exit(0)
if not (a.cues and a.out and a.duration): ap.error('faltam deixas, saída ou --duration')

def find(name):
    """Primeiro na própria pasta (ou no caminho relativo dado, ex. kenney-interface/click_001), depois em qualquer subpasta."""
    for d in DIRS:
        hits = sorted(f for f in d.glob(name + '.*') if f.suffix.lower() in AUDIO_EXT)
        if hits: return hits[0]
    for d in DIRS:
        hits = sorted(f for f in d.rglob(pathlib.Path(name).name + '.*') if f.suffix.lower() in AUDIO_EXT)
        if hits: return hits[0]
    sys.exit(f'som "{name}" não existe em {a.dir}/ nem na biblioteca {LIB}/ (ver --list)')

cache = {}
def load(name, pitch):
    """Som em estéreo float32, com a altura alterada e sem o silêncio inicial."""
    if (name, pitch) not in cache:
        af = f'asetrate={SR}*{pitch},aresample={SR}' if pitch != 1 else f'aresample={SR}'
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(find(name)), '-af', f'aresample={SR},{af}', '-ac', '2', '-f', 'f32le', '-'],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2).copy()
        loud = np.nonzero(np.abs(x).max(axis=1) > 0.02 * np.abs(x).max())[0]     # corta o silêncio antes do ataque (-34 dB do pico)
        cache[(name, pitch)] = x[max(0, loud[0] - int(0.004 * SR)):] if len(loud) else x
    return cache[(name, pitch)]

mix = np.zeros((int(a.duration * SR), 2), dtype=np.float32); n = 0
for ln, raw in enumerate(pathlib.Path(a.cues).read_text().splitlines(), 1):
    f = raw.split('#')[0].split()
    if not f: continue
    if len(f) < 3: sys.exit(f'linha {ln}: esperava "tempo som pico_dB [pitch] [inicio] [duracao]"')
    t, name, peak = float(f[0]), f[1], float(f[2])
    pitch = float(f[3]) if len(f) > 3 else 1.0
    x = load(name, pitch)
    if len(f) > 4:
        i0 = int(float(f[4]) * SR); x = x[i0:i0 + int(float(f[5]) * SR)] if len(f) > 5 else x[i0:]
        fade = min(int(0.12 * SR), len(x) // 3); x = x.copy(); ramp = np.linspace(0, 1, fade)[:, None]; x[:fade] *= ramp; x[-fade:] *= ramp[::-1]
    pk = np.abs(x).max()
    if pk == 0: continue
    x = x / pk * 10 ** (peak / 20)
    i = int(t * SR); x = x[:max(0, len(mix) - i)]
    tail = min(int(0.01 * SR), len(x)); x = x.copy(); x[-tail:] *= np.linspace(1, 0, tail)[:, None]     # sem estalo se for cortado no fim
    mix[i:i + len(x)] += x; n += 1
pk = np.abs(mix).max()
if pk > 0.95: mix *= 0.95 / pk
with wave.open(a.out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'{a.out}: {n} deixas, {a.duration} s, pico {20 * np.log10(max(pk, 1e-9)):.1f} dB')
