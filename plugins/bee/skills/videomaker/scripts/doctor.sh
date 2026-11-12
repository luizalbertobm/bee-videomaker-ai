#!/usr/bin/env bash
# Diagnóstico das dependências do videomaker. Uso: bash doctor.sh (a partir da raiz do projeto)
ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
no() { printf "  \033[31m✗\033[0m %s\n    → %s\n" "$1" "$2"; MISSING=1; }
MISSING=0
echo "Ferramentas:"
command -v ffmpeg >/dev/null && ok "ffmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3)" || no "ffmpeg/ffprobe" "sudo apt install ffmpeg"
command -v bc >/dev/null && ok "bc" || no "bc" "sudo apt install bc"
command -v python3 >/dev/null && ok "python3 $(python3 --version | cut -d' ' -f2)" || no "python3" "sudo apt install python3"
python3 -c "import playwright" 2>/dev/null && ok "playwright (Python)" || no "playwright (Python)" "pip install playwright"
if command -v google-chrome >/dev/null || command -v google-chrome-stable >/dev/null; then ok "Google Chrome (render usa channel=chrome)"; else no "Google Chrome" "instalar Chrome, ou 'playwright install chromium' e trocar channel=\"chrome\" por chromium em render_canvas.py"; fi
python3 -c "import faster_whisper" 2>/dev/null && ok "faster-whisper (transcrição local)" || no "faster-whisper" "pip install faster-whisper   # opcional: nvidia-cublas-cu12 nvidia-cudnn-cu12 para GPU"
python3 -c "import PIL" 2>/dev/null && ok "Pillow (folhas de contacto)" || no "Pillow" "pip install pillow"
echo "Projeto ($(pwd)):"
[[ -d sources/logos ]] && ok "sources/logos/ ($(ls sources/logos 2>/dev/null | wc -l) itens)" || no "sources/logos/" "criar e pôr os logos (SVG/PNG) da marca"
[[ -d sources/fonts ]] && ok "sources/fonts/ ($(ls sources/fonts/*.ttf 2>/dev/null | wc -l) .ttf)" || no "sources/fonts/" "criar e pôr as fontes .ttf da marca (os modelos esperam display.ttf e body.ttf; ajustar FONT_FACES no template)"
[[ -f sources/identidade-visual.md ]] && ok "sources/identidade-visual.md" || echo "  · sources/identidade-visual.md ausente (opcional: resumo do manual da marca)"
if [[ -f .env ]]; then grep -q '^PIXABAY_API_KEY=.\+' .env && ok "PIXABAY_API_KEY no .env" || echo "  · PIXABAY_API_KEY vazia no .env (stock de vídeo desativado)"; else echo "  · .env ausente (opcional: PIXABAY_API_KEY para stock de vídeo)"; fi
echo "Conectores (verificar na sessão do Claude):"
echo "  · ElevenLabs (tools creative_*) — obrigatório para narração e música"
echo "  · Higgsfield — opcional, para imagens/vídeo gerados"
[[ $MISSING -eq 0 ]] && echo "Tudo pronto." || { echo "Faltam itens acima."; exit 1; }
