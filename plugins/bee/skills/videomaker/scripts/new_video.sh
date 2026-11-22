#!/usr/bin/env bash
# Cria a pasta de um vídeo novo, com a estrutura que os outros scripts esperam. Correr a partir da raiz do projeto.
#   bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/new_video.sh reel-lancamento        # → videos/AAAA-MM-reel-lancamento/
#   bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/new_video.sh 2026-11-reel-lancamento # nome já com data: usado tal como está
#
# Estrutura do projeto (nomes fixos; ver SKILL.md):
#   brand/                  logos/, fonts/, icons/lucide/, brand-guide.md — partilhado por todos os vídeos
#   library/                stock/, sfx/, music/, credits.md — material reutilizável e o registo de créditos
#   references/<id>/        análises de vídeos de terceiros (referencia.py); nunca entram num vídeo
#   videos/<slug>/
#     script.md             roteiro
#     production/inputs/    material do cliente para este vídeo (narração gravada, capturas de site, filmagens)
#     production/scenes/    NN.html, NN.mp4|png (+ icons.js, devices.js)
#     production/audio/     NN.mp3, sfx.wav
#     production/sfx.tsv, subtitles.srt, music.mp3 (opcionais)
#     production/build/     intermediários e review/ (fora do git)
#     deliverables/         <slug>-vN.mp4 e credits.md — só o que se entrega
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:-}"
if [[ -z "$NAME" ]]; then echo "Uso: new_video.sh <slug>   (ex. reel-lancamento)" >&2; exit 2; fi
# slug: minúsculas, números e hífens
SLUG=$(printf '%s' "$NAME" | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null || printf '%s' "$NAME")
SLUG=$(printf '%s' "$SLUG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')
[[ -z "$SLUG" ]] && { echo "Nome inválido: $NAME" >&2; exit 2; }
[[ "$SLUG" =~ ^[0-9]{4}-[0-9]{2}- ]] || SLUG="$(date +%Y-%m)-$SLUG"
V="videos/$SLUG"
if [[ -e "$V" ]]; then echo "Já existe: $V (escolher outro nome ou continuar nessa pasta)" >&2; exit 1; fi

mkdir -p "$V"/production/{inputs,scenes,audio,build} "$V"/deliverables brand/logos brand/fonts library/stock library/sfx library/music
printf '*\n' > "$V/production/build/.gitignore"
cp "$SKILL_DIR/assets/script.md" "$V/script.md"
cp "$SKILL_DIR/assets/icons.js" "$SKILL_DIR/assets/devices.js" "$V/production/scenes/"
echo "$V"
