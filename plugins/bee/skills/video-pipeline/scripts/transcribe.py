#!/usr/bin/env python3
"""Transcreve áudio localmente com faster-whisper (Whisper em CTranslate2), sem custos nem rede
depois do primeiro download do modelo. Produz .txt, .srt, .vtt e .json com timestamps por palavra.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/transcribe.py sources/narracao.mp3
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/transcribe.py audio/*.mp3 --language pt --out-dir legendas
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/transcribe.py audio/02.mp3 --max-chars 24   # legendas curtas p/ reels

Modelos (download automático para ~/.cache/huggingface na primeira vez):
  large-v3   melhor qualidade, multilingue, ~3 GB      (por omissão)
  medium     boa qualidade, ~1,5 GB
  small      rápido, ~500 MB, serve para rascunhos
  distil-large-v3  muito rápido mas só inglês

Dispositivo: --device auto tenta a GPU (CUDA) e cai para CPU int8 se faltarem as bibliotecas CUDA.
Requer: pip install faster-whisper ; ffmpeg no PATH (descodificação).
"""
import argparse, json, pathlib, sys, time


def fmt_ts(sec: float, vtt: bool = False) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
    sep = '.' if vtt else ','
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def regroup_by_chars(words, max_chars):
    """Reagrupa palavras em blocos curtos (legendas de reel), quebrando também em pontuação forte."""
    blocks, cur = [], []
    def flush():
        if cur:
            blocks.append({'start': cur[0]['start'], 'end': cur[-1]['end'],
                           'text': ''.join(w['word'] for w in cur).strip()})
            cur.clear()
    for w in words:
        candidate = ''.join(x['word'] for x in cur) + w['word']
        if cur and len(candidate.strip()) > max_chars:
            flush()
        cur.append(w)
        if w['word'].rstrip().endswith(('.', '!', '?', ':', ';')):
            flush()
    flush()
    return blocks


def write_outputs(stem: pathlib.Path, segments, info, formats, words_all):
    out = {}
    if 'txt' in formats:
        p = stem.with_suffix('.txt'); p.write_text(' '.join(s['text'] for s in segments).strip() + '\n'); out['txt'] = p
    if 'srt' in formats:
        p = stem.with_suffix('.srt')
        p.write_text(''.join(f"{i}\n{fmt_ts(s['start'])} --> {fmt_ts(s['end'])}\n{s['text']}\n\n"
                             for i, s in enumerate(segments, 1)))
        out['srt'] = p
    if 'vtt' in formats:
        p = stem.with_suffix('.vtt')
        p.write_text('WEBVTT\n\n' + ''.join(f"{fmt_ts(s['start'], True)} --> {fmt_ts(s['end'], True)}\n{s['text']}\n\n"
                                            for s in segments))
        out['vtt'] = p
    if 'json' in formats:
        p = stem.with_suffix('.json')
        p.write_text(json.dumps({'language': info.language, 'language_probability': round(info.language_probability, 3),
                                 'duration': round(info.duration, 3), 'segments': segments, 'words': words_all},
                                ensure_ascii=False, indent=1))
        out['json'] = p
    return out


def preload_cuda_libs():
    """O CTranslate2 precisa de libcublas.so.12 e libcudnn*.so.9. Se vieram por pip
    (nvidia-cublas-cu12, nvidia-cudnn-cu12) não estão no LD_LIBRARY_PATH; carregá-las aqui
    com ctypes faz o dlopen posterior encontrá-las. Sem elas, cai-se para CPU."""
    import ctypes, importlib
    loaded = 0
    for mod, names in (('nvidia.cublas', ['libcublasLt.so.12', 'libcublas.so.12']),
                       ('nvidia.cudnn', ['libcudnn.so.9', 'libcudnn_ops.so.9', 'libcudnn_cnn.so.9'])):
        try:
            lib = pathlib.Path(importlib.import_module(mod).__path__[0]) / 'lib'
            for n in names:
                p = lib / n
                if p.exists():
                    ctypes.CDLL(str(p), mode=ctypes.RTLD_GLOBAL); loaded += 1
        except Exception:
            pass
    return loaded


def load_model(name, device, compute_type):
    from faster_whisper import WhisperModel
    if device in ('auto', 'cuda'):
        preload_cuda_libs()
        try:
            m = WhisperModel(name, device='cuda', compute_type=compute_type or 'float16')
            return m, 'cuda'
        except Exception as e:  # sem GPU, driver antigo, etc.
            if device == 'cuda':
                raise
            print(f"[aviso] GPU indisponível ({type(e).__name__}: {e}); a usar CPU int8.", file=sys.stderr)
    return WhisperModel(name, device='cpu', compute_type=compute_type or 'int8'), 'cpu'


def load_cpu(name, compute_type):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device='cpu', compute_type=compute_type or 'int8'), 'cpu'


def main():
    ap = argparse.ArgumentParser(description='Transcrição local com faster-whisper.')
    ap.add_argument('audio', nargs='+', help='ficheiros de áudio ou vídeo (qualquer formato que o ffmpeg leia)')
    ap.add_argument('--model', default='large-v3')
    ap.add_argument('--language', default=None, help='código ISO (pt, en, ...); omitir para detetar')
    ap.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda'])
    ap.add_argument('--compute-type', default=None, help='float16 | int8 | int8_float16 (por omissão: float16 na GPU, int8 na CPU)')
    ap.add_argument('--out-dir', default=None, help='pasta de saída (por omissão: ao lado do áudio)')
    ap.add_argument('--formats', default='txt,srt,vtt,json')
    ap.add_argument('--max-chars', type=int, default=None, help='reagrupar em legendas de até N caracteres (usa timestamps por palavra)')
    ap.add_argument('--no-vad', action='store_true', help='não filtrar silêncios com VAD')
    ap.add_argument('--beam-size', type=int, default=5)
    ap.add_argument('--initial-prompt', default=None, help='vocabulário/estilo esperado, ex. "Nome da Marca. Slogan da marca."')
    a = ap.parse_args()
    formats = {f.strip() for f in a.formats.split(',')}

    t0 = time.time()
    model, device = load_model(a.model, a.device, a.compute_type)
    print(f"modelo {a.model} em {device} ({time.time() - t0:.1f} s a carregar)")

    for f in a.audio:
        src = pathlib.Path(f)
        if not src.exists():
            print(f"[erro] não existe: {src}", file=sys.stderr); continue
        t1 = time.time()
        opts = dict(language=a.language, beam_size=a.beam_size, word_timestamps=True, vad_filter=not a.no_vad,
                    initial_prompt=a.initial_prompt, condition_on_previous_text=False)
        try:
            seg_iter, info = model.transcribe(str(src), **opts)
            segments_raw = list(seg_iter)
        except RuntimeError as e:
            # O erro de bibliotecas CUDA só aparece na primeira computação, não ao carregar o modelo.
            if device != 'cuda' or a.device == 'cuda':
                raise
            print(f"[aviso] falha na GPU ({e}); a recarregar em CPU int8.", file=sys.stderr)
            model, device = load_cpu(a.model, None)
            seg_iter, info = model.transcribe(str(src), **opts)
            segments_raw = list(seg_iter)
        segments, words_all = [], []
        for s in segments_raw:
            words = [{'word': w.word, 'start': round(w.start, 3), 'end': round(w.end, 3), 'p': round(w.probability, 2)}
                     for w in (s.words or [])]
            words_all += words
            segments.append({'start': round(s.start, 3), 'end': round(s.end, 3), 'text': s.text.strip()})
        if a.max_chars and words_all:
            segments = regroup_by_chars(words_all, a.max_chars)
        out_dir = pathlib.Path(a.out_dir) if a.out_dir else src.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        outs = write_outputs(out_dir / src.stem, segments, info, formats, words_all)
        text = ' '.join(s['text'] for s in segments).strip()
        print(f"\n{src.name}: {info.duration:.2f} s de áudio, idioma {info.language} (p={info.language_probability:.2f}), "
              f"{len(segments)} segmentos, {time.time() - t1:.1f} s a transcrever")
        print(f"  texto: {text}")
        for k, p in outs.items():
            print(f"  {k}: {p}")


if __name__ == '__main__':
    main()
