#!/usr/bin/env bash
# Monta o vídeo final a partir das cenas e narrações do projeto.
# Uso (a partir da raiz do projeto): bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/montagem.ffmpeg.sh saida.mp4
# Formato/fps/qualidade por ambiente: W=1920 H=1080 FPS=30 CRF=18 bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/montagem.ffmpeg.sh saida.mp4
# Música de fundo: musica.mp3 na raiz (ou MUSIC=ficheiro), volume MUSIC_VOL (0.35 por omissão), com ducking sob a narração.
# Efeitos sonoros: SFX=faixa.wav (feita por sfx_track.py a partir de uma folha de deixas), volume SFX_VOL (1 por omissão).
# Volume final: normalizado a LUFS=-14 (integrado, alvo de Instagram/TikTok/YouTube) com pico verdadeiro ≤ TP=-1.5 dBTP,
# em duas passagens de loudnorm; LUFS=0 desliga.
#
# Estrutura esperada:
#   scenes/NN.mp4|webm|png|jpg   cena NN (Canvas já renderizado por ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/render_canvas.py, ou Higgsfield)
#   audio/NN.mp3                 narração da cena NN (opcional)
#   legendas.srt                 legendas (opcional)
# Narração mais curta que a cena é preenchida com silêncio (apad), para -shortest cortar pelo vídeo e não pelo áudio.
# O áudio original das cenas é descartado (modelos como o Seedance geram áudio próprio); só a narração entra.
set -euo pipefail
export LC_ALL=C   # números com ponto decimal em awk/printf, senão o ffmpeg lê "18,38" como dois filtros
OUT="${1:-video.mp4}"
SCENES="${SCENES:-scenes}"; AUDIO="${AUDIO:-audio}"   # pastas (ex. SCENES=scenes/v2 para uma segunda versão sem sobrescrever a primeira)
W="${W:-1080}"; H="${H:-1920}"; FPS="${FPS:-30}"
CRF="${CRF:-20}"   # qualidade x264 das cenas normalizadas (menor = melhor; 18 para vídeo real com muito detalhe)
mkdir -p build
# Todas as cenas saem com uma faixa de áudio uniforme (AAC mono 44.1 kHz): cenas sem narração levam silêncio.
# Sem isto o concat com -c copy falha ao misturar cenas com e sem áudio.
SILENCE="anullsrc=channel_layout=mono:sample_rate=44100"
AENC=(-c:a aac -ac 1 -ar 44100 -b:a 128k)

shopt -s nullglob
scenes=("$SCENES"/*.mp4 "$SCENES"/*.webm "$SCENES"/*.png "$SCENES"/*.jpg)
if [[ ${#scenes[@]} -eq 0 ]]; then echo "Nenhuma cena em $SCENES/"; exit 1; fi
IFS=$'\n' scenes=($(printf '%s\n' "${scenes[@]}" | sort)); unset IFS

: > build/list.txt
for f in "${scenes[@]}"; do
  n=$(basename "${f%.*}")
  a="$AUDIO/$n.mp3"
  if [[ "$f" == *.png || "$f" == *.jpg ]]; then
    # Imagem fixa: duração = duração do áudio (ou 4 s), com zoom lento (Ken Burns)
    if [[ -f "$a" ]]; then d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$a"); AUD=(-i "$a"); else d=4; AUD=(-f lavfi -i "$SILENCE"); fi
    frames=$(awk -v d="$d" -v f="$FPS" 'BEGIN{printf "%d", d*f}')
    ffmpeg -y -loglevel error -loop 1 -i "$f" "${AUD[@]}" -t "$d" \
      -vf "scale=${W}*1.1:-2,zoompan=z='min(zoom+0.0008,1.1)':d=${frames}:s=${W}x${H}:fps=$FPS" \
      -map 0:v:0 -map 1:a:0 "${AENC[@]}" -c:v libx264 -crf "$CRF" -pix_fmt yuv420p -shortest "build/$n.mp4"
  else
    if [[ -f "$a" ]]; then AUD=(-i "$a"); else AUD=(-f lavfi -i "$SILENCE"); fi
    ffmpeg -y -loglevel error -i "$f" "${AUD[@]}" \
      -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,fps=$FPS" \
      -map 0:v:0 -map 1:a:0 -af apad "${AENC[@]}" -c:v libx264 -crf "$CRF" -pix_fmt yuv420p -shortest "build/$n.mp4"
  fi
  echo "file '$n.mp4'" >> build/list.txt
  echo "cena $n ok"
done

# Concatenar
ffmpeg -y -loglevel error -f concat -safe 0 -i build/list.txt -c copy build/concat.mp4

# Música de fundo (opcional): MUSIC=caminho ou musica.mp3 na raiz. Entra em loop/corte à duração do vídeo,
# com fade in/out e ducking: baixa quando a narração fala (sidechaincompress) e volta a subir nas pausas.
MUSIC="${MUSIC:-musica.mp3}"; MUSIC_VOL="${MUSIC_VOL:-0.35}"
STAGE=build/concat.mp4
if [[ -f "$MUSIC" ]]; then
  D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 build/concat.mp4)
  FO=$(awk -v d="$D" 'BEGIN{printf "%.2f", d-1.5}')
  ffmpeg -y -loglevel error -i build/concat.mp4 -stream_loop -1 -i "$MUSIC" -filter_complex \
    "[1:a]atrim=0:${D},asetpts=PTS-STARTPTS,volume=${MUSIC_VOL},afade=t=in:d=1,afade=t=out:st=${FO}:d=1.5[m];\
     [0:a]asplit=2[voz][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=40:release=500:makeup=1[duck];\
     [voz][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" \
    -map 0:v:0 -map "[a]" -c:v copy "${AENC[@]}" -ac 2 build/mixed.mp4
  STAGE=build/mixed.mp4; echo "música: $MUSIC (vol $MUSIC_VOL, ducking)"
fi

# Efeitos sonoros (opcional): SFX=faixa.wav feita por scripts/sfx_track.py, já com a duração do vídeo e cada som no seu instante.
# Entra por cima da voz e da música sem ducking; SFX_VOL ajusta o conjunto (1 por omissão).
SFX="${SFX:-}"; SFX_VOL="${SFX_VOL:-1}"
if [[ -n "$SFX" && -f "$SFX" ]]; then
  ffmpeg -y -loglevel error -i "$STAGE" -i "$SFX" -filter_complex \
    "[1:a]volume=${SFX_VOL}[fx];[0:a][fx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]" \
    -map 0:v:0 -map "[a]" -c:v copy "${AENC[@]}" -ac 2 build/sfx.mp4
  STAGE=build/sfx.mp4; echo "efeitos: $SFX (vol $SFX_VOL)"
fi

LUFS="${LUFS:--14}"; TP="${TP:--1.5}"
if [[ "$LUFS" != "0" ]]; then
  # 1.ª passagem mede, 2.ª aplica um ganho linear (sem compressão dinâmica) com os valores medidos
  m=$(ffmpeg -hide_banner -i "$STAGE" -vn -af "loudnorm=I=$LUFS:TP=$TP:LRA=11:print_format=json" -f null - 2>&1 \
      | python3 -c 'import sys,json; t=sys.stdin.read(); d=json.loads(t[t.rindex("{"):]); print(d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"], d["target_offset"])')
  read -r mi mtp mlra mth off <<< "$m"
  ch=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of csv=p=0 "$STAGE")
  vd=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$STAGE")   # o loudnorm alonga o áudio ~0,1 s; -shortest com -c:v copy cortava 3 s
  ffmpeg -y -loglevel error -i "$STAGE" -af \
    "loudnorm=I=$LUFS:TP=$TP:LRA=11:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true,atrim=0:$vd" \
    -map 0:v:0 -map 0:a:0 -c:v copy "${AENC[@]}" -ac "$ch" build/loud.mp4
  STAGE=build/loud.mp4; echo "volume: $mi LUFS -> $LUFS LUFS (pico ≤ $TP dBTP)"
fi

# Legendas (se existirem)
if [[ -f legendas.srt ]]; then
  ffmpeg -y -loglevel error -i "$STAGE" -vf "subtitles=legendas.srt:force_style='FontSize=18,Outline=1'" -c:a copy "$OUT"
else
  cp "$STAGE" "$OUT"
fi
echo "Pronto: $OUT ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT") s)"
