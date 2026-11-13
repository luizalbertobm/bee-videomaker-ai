#!/usr/bin/env bash
# Diagnóstico e preparação do videomaker. Correr a partir da raiz do projeto.
#   bash doctor.sh              relatório legível (sai com 1 se faltar algo obrigatório)
#   bash doctor.sh --json       o mesmo em JSON, passo a passo, para o assistente do /bee:doctor (inclui first_run)
#   bash doctor.sh --smoke      teste real da cadeia: renderiza uma cena mínima, ícone, faixa de efeitos e montagem
#   bash doctor.sh --mark-done  regista que a preparação deste projeto ficou concluída (.videomaker/setup.json)
#   bash doctor.sh --reset      apaga esse registo (a próxima execução volta a ser a "primeira")
# "Primeira execução" = o projeto ainda não tem .videomaker/setup.json. A pasta .videomaker/ ignora-se a si própria no git.
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKER=".videomaker/setup.json"
MODE="${1:-}"

# ---------- registo de primeira execução ----------
if [[ "$MODE" == "--mark-done" ]]; then
  mkdir -p .videomaker && printf '*\n' > .videomaker/.gitignore
  printf '{"setup_done":"%s","plugin":"bee","skill":"videomaker"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$MARKER"
  echo "Preparação registada em $MARKER"; exit 0
fi
if [[ "$MODE" == "--reset" ]]; then rm -f "$MARKER"; echo "Registo apagado: a próxima execução do /bee:doctor volta a ser guiada."; exit 0; fi

# ---------- teste real da cadeia ----------
if [[ "$MODE" == "--smoke" ]]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; FAIL=0
  step() { if "${@:2}" >"$T/log" 2>&1; then printf "  \033[32m✓\033[0m %s\n" "$1"; else printf "  \033[31m✗\033[0m %s\n" "$1"; sed 's/^/      /' "$T/log" | tail -6; FAIL=1; fi; }
  mkdir -p "$T/scenes"
  cat > "$T/scenes/01.html" <<'HTML'
<!doctype html><html><body style="margin:0"><canvas id="c"></canvas><script>
const WIDTH = 270, HEIGHT = 480, FPS = 30, DURATION_S = 0.5;
const c = document.getElementById('c'); c.width = WIDTH; c.height = HEIGHT; const ctx = c.getContext('2d');
function renderFrame(t) { ctx.fillStyle = '#101828'; ctx.fillRect(0, 0, WIDTH, HEIGHT); ctx.fillStyle = '#ffb703'; ctx.beginPath(); ctx.arc(WIDTH / 2, HEIGHT / 2, 20 + 160 * t, 0, 7); ctx.fill(); }
</script></body></html>
HTML
  echo "Teste da cadeia (pasta temporária):"
  render() { (cd "$T" && python3 "$SKILL_DIR/scripts/render_canvas.py" scenes/01.html scenes/01.mp4 && [[ "$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 scenes/01.mp4)" == 15 ]]); }
  icon() { (cd "$T" && python3 "$SKILL_DIR/scripts/icons.py" rocket && grep -q '"rocket"' sources/icons/lucide/icons.js); }
  sfx() { (cd "$T" && printf '0.05 pop -18\n0.25 click_001 -16\n' > cues.tsv && python3 "$SKILL_DIR/scripts/sfx_track.py" cues.tsv sfx.wav --duration 0.5 && [[ -s sfx.wav ]]); }
  mount() { (cd "$T" && SFX=sfx.wav bash "$SKILL_DIR/scripts/montagem.ffmpeg.sh" final.mp4 && [[ -s final.mp4 ]]); }
  sheet() { (cd "$T" && python3 "$SKILL_DIR/scripts/contact_sheet.py" final.mp4 --frames 4 --width 120 --out folha.png && [[ -s folha.png ]]); }
  step "Cena Canvas → MP4 (Chrome + Playwright + ffmpeg)" render
  step "Ícone Lucide do pacote local" icon
  step "Faixa de efeitos sonoros (numpy + biblioteca local)" sfx
  step "Montagem final com efeitos" mount
  step "Folha de contacto (ffmpeg)" sheet
  [[ $FAIL -eq 0 ]] && echo "A cadeia funciona de ponta a ponta." || { echo "Há passos a falhar acima."; exit 1; }
  exit 0
fi

# ---------- verificações (uma entrada por passo do assistente) ----------
I_ID=(); I_GRP=(); I_REQ=(); I_ST=(); I_LBL=(); I_DET=(); I_FIX=()
add() { I_ID+=("$1"); I_GRP+=("$2"); I_REQ+=("$3"); I_ST+=("$4"); I_LBL+=("$5"); I_DET+=("$6"); I_FIX+=("$7"); }
has() { command -v "$1" >/dev/null 2>&1; }
pymod() { python3 -c "import $1" >/dev/null 2>&1; }

# gestor de pacotes do sistema, para dar o comando certo
if has apt-get; then PM=apt; SYS="sudo apt install -y"; PY_PKG="python3 python3-pip"
elif has dnf; then PM=dnf; SYS="sudo dnf install -y"; PY_PKG="python3 python3-pip"
elif has pacman; then PM=pacman; SYS="sudo pacman -S --needed"; PY_PKG="python python-pip"
elif has brew; then PM=brew; SYS="brew install"; PY_PKG="python"
else PM=desconhecido; SYS="instalar com o gestor de pacotes do sistema:"; PY_PKG="python3"; fi
# pip: em sistemas com Python "externally managed" (Debian 12+, Ubuntu 23.04+) fora de um venv, o pip recusa sem esta flag
PIP="python3 -m pip install --user"
if has python3 && [[ -z "${VIRTUAL_ENV:-}" ]] && python3 -c "import sysconfig,os,sys;sys.exit(0 if os.path.exists(os.path.join(sysconfig.get_path('stdlib'),'EXTERNALLY-MANAGED')) else 1)" 2>/dev/null; then PIP="$PIP --break-system-packages"; fi
[[ -n "${VIRTUAL_ENV:-}" ]] && PIP="python3 -m pip install"

# 1. sistema
if has ffmpeg && has ffprobe; then add ffmpeg sistema 1 ok "ffmpeg e ffprobe" "$(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3)" ""; else add ffmpeg sistema 1 missing "ffmpeg e ffprobe" "codificam cada cena e fazem a montagem final" "$SYS ffmpeg"; fi
if has bc; then add bc sistema 1 ok "bc" "" ""; else add bc sistema 1 missing "bc" "contas de durações no script de montagem" "$SYS bc"; fi
if has python3; then add python3 sistema 1 ok "python3" "$(python3 --version 2>&1 | cut -d' ' -f2)" ""; else add python3 sistema 1 missing "python3" "corre os scripts da skill" "$SYS $PY_PKG"; fi

# 2. pacotes Python
pymod playwright && add playwright python 1 ok "playwright (Python)" "" "" || add playwright python 1 missing "playwright (Python)" "comanda o Chrome para desenhar cada frame das cenas Canvas" "$PIP playwright"
pymod numpy && add numpy python 1 ok "numpy" "" "" || add numpy python 1 missing "numpy" "mistura a faixa de efeitos sonoros (sfx_track.py)" "$PIP numpy"
pymod yt_dlp && add yt-dlp python 0 ok "yt-dlp" "$(python3 -m yt_dlp --version 2>/dev/null)" "" || add yt-dlp python 0 missing "yt-dlp" "opcional: descarrega vídeos de referência para o referencia.py (manter atualizado)" "$PIP -U yt-dlp"
pymod faster_whisper && add faster-whisper python 1 ok "faster-whisper" "" "" || add faster-whisper python 1 missing "faster-whisper" "transcrição local e legendas (o modelo large-v3, ~3 GB, é descarregado no primeiro uso)" "$PIP faster-whisper"

# 3. Chrome
if has google-chrome || has google-chrome-stable || [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then add chrome chrome 1 ok "Google Chrome" "o render usa channel=chrome" ""
else
  case "$PM" in
    apt) CFIX="wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo apt install -y ./google-chrome-stable_current_amd64.deb" ;;
    dnf) CFIX="sudo dnf install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm" ;;
    brew) CFIX="brew install --cask google-chrome" ;;
    *) CFIX="instalar de https://www.google.com/chrome/" ;;
  esac
  add chrome chrome 1 missing "Google Chrome" "desenha as cenas Canvas frame a frame; alternativa: 'python3 -m playwright install chromium' e trocar channel=\"chrome\" por chromium em render_canvas.py" "$CFIX"
fi

# 4. projeto: pastas, logos, fontes
MISS_DIRS=""; for d in sources/logos sources/fonts scenes audio build; do [[ -d "$d" ]] || MISS_DIRS="$MISS_DIRS $d"; done
[[ -z "$MISS_DIRS" ]] && add pastas projeto 1 ok "pastas do projeto" "sources/logos, sources/fonts, scenes, audio, build" "" || add pastas projeto 1 missing "pastas do projeto" "faltam:$MISS_DIRS" "mkdir -p$MISS_DIRS"
NLOGOS=$(find sources/logos -type f \( -iname '*.svg' -o -iname '*.png' \) 2>/dev/null | wc -l | tr -d ' ')
[[ "$NLOGOS" -gt 0 ]] && add logos projeto 1 ok "logos da marca" "$NLOGOS ficheiros em sources/logos/" "" || add logos projeto 1 missing "logos da marca" "os logos nunca são gerados por modelos: usam-se os ficheiros oficiais" "copiar os logos (SVG de preferência, PNG como alternativa) para sources/logos/"
# as fontes esperadas leem-se do próprio modelo de cena (FONT_FACES), por isso este script serve qualquer marca
WANT=$(grep -o "sources/fonts/[^'\"]*\.[ot]tf" "$SKILL_DIR/assets/canvas-scene.html" 2>/dev/null | sort -u)
MISS_FONTS=""; for f in $WANT; do [[ -f "$f" ]] || MISS_FONTS="$MISS_FONTS $(basename "$f")"; done
NFONTS=$(find sources/fonts -type f \( -iname '*.ttf' -o -iname '*.otf' \) 2>/dev/null | wc -l | tr -d ' ')
if [[ -z "$MISS_FONTS" && "$NFONTS" -gt 0 ]]; then add fontes projeto 1 ok "fontes da marca" "$NFONTS ficheiros em sources/fonts/" ""
else add fontes projeto 1 missing "fontes da marca" "os modelos de cena carregam:$(for f in $WANT; do printf ' %s' "$(basename "$f")"; done); em falta:${MISS_FONTS:- (nenhuma fonte na pasta)}" "copiar as fontes .ttf da marca para sources/fonts/ com esses nomes, ou ajustar FONT_FACES nas cenas"; fi

# 5. opcionais do projeto
if [[ -f sources/identidade-visual.md || -f identidade-visual.md ]]; then add identidade marca 0 ok "identidade-visual.md" "resumo do manual da marca" ""
else add identidade marca 0 missing "identidade-visual.md" "opcional: cores oficiais, fontes e regras do logo; sem ele pergunta-se a paleta em cada briefing" "criar sources/identidade-visual.md com paleta (fundo, texto, acento), fonte de display e de corpo, e regras de uso do logo"; fi
if [[ -f .env ]] && grep -q '^PIXABAY_API_KEY=.\+' .env; then add pixabay stock 0 ok "chave do Pixabay" "PIXABAY_API_KEY no .env" ""
else add pixabay stock 0 missing "chave do Pixabay" "opcional: sem ela não há stock de vídeo (o Openverse continua a dar imagens e sons)" "criar conta em https://pixabay.com/api/docs/ e escrever PIXABAY_API_KEY=... no ficheiro .env da raiz do projeto"; fi

# 6. conectores: só a sessão do Claude os consegue ver
add elevenlabs conectores 1 check "conector ElevenLabs" "tools creative_* (ex. creative_generate_speech): narração e música" "ligar o conector ElevenLabs ao Claude; ver references/setup-mcp.md"
add higgsfield conectores 0 check "conector Higgsfield" "opcional: tools generate_image / generate_video para cenas geradas" "ligar o conector Higgsfield; ver references/setup-mcp.md"

REQ_MISSING=0; OPT_MISSING=0
for i in "${!I_ID[@]}"; do [[ "${I_ST[$i]}" == missing ]] && { [[ "${I_REQ[$i]}" == 1 ]] && REQ_MISSING=$((REQ_MISSING + 1)) || OPT_MISSING=$((OPT_MISSING + 1)); }; done
[[ -f "$MARKER" ]] && FIRST=false || FIRST=true

# ---------- saída JSON ----------
if [[ "$MODE" == "--json" ]]; then
  esc() { local s="$1"; s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; printf '%s' "$s"; }
  printf '{"first_run":%s,"marker":"%s","project":"%s","package_manager":"%s","missing_required":%d,"missing_optional":%d,"steps":[' \
    "$FIRST" "$MARKER" "$(esc "$(pwd)")" "$PM" "$REQ_MISSING" "$OPT_MISSING"
  for i in "${!I_ID[@]}"; do
    [[ $i -gt 0 ]] && printf ','
    printf '\n {"id":"%s","group":"%s","required":%s,"status":"%s","label":"%s","detail":"%s","fix":"%s"}' \
      "${I_ID[$i]}" "${I_GRP[$i]}" "$([[ "${I_REQ[$i]}" == 1 ]] && echo true || echo false)" "${I_ST[$i]}" \
      "$(esc "${I_LBL[$i]}")" "$(esc "${I_DET[$i]}")" "$(esc "${I_FIX[$i]}")"
  done
  printf '\n]}\n'; exit 0
fi

# ---------- saída legível ----------
title() { case "$1" in sistema) echo "Sistema:";; python) echo "Pacotes Python:";; chrome) echo "Browser:";; projeto) echo "Projeto ($(pwd)):";; marca) echo "Marca:";; stock) echo "Stock gratuito:";; conectores) echo "Conectores (verificar na sessão do Claude):";; esac; }
LAST=""
for i in "${!I_ID[@]}"; do
  [[ "${I_GRP[$i]}" != "$LAST" ]] && { title "${I_GRP[$i]}"; LAST="${I_GRP[$i]}"; }
  case "${I_ST[$i]}" in
    ok) printf "  \033[32m✓\033[0m %s%s\n" "${I_LBL[$i]}" "${I_DET[$i]:+ (${I_DET[$i]})}" ;;
    check) printf "  · %s — %s\n" "${I_LBL[$i]}" "${I_DET[$i]}" ;;
    missing) if [[ "${I_REQ[$i]}" == 1 ]]; then printf "  \033[31m✗\033[0m %s — %s\n    → %s\n" "${I_LBL[$i]}" "${I_DET[$i]}" "${I_FIX[$i]}"; else printf "  · %s em falta — %s\n    → %s\n" "${I_LBL[$i]}" "${I_DET[$i]}" "${I_FIX[$i]}"; fi ;;
  esac
done
[[ "$FIRST" == true ]] && echo "Primeira execução neste projeto: /bee:doctor guia a preparação passo a passo."
[[ $REQ_MISSING -eq 0 ]] && echo "Tudo o que é obrigatório está pronto." || { echo "Faltam $REQ_MISSING itens obrigatórios (✗ acima)."; exit 1; }
