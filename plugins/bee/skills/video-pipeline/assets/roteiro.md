# Roteiro — <título do vídeo>

- Objetivo:
- Público:
- Duração total: <s>
- Formato: 9:16 | 16:9 | 1:1
- Idioma / voz:
- Estilo visual (paleta, tipografia, referências): <cores do manual da marca ou do briefing; fonte de display e de corpo>
- Fontes já disponíveis em `sources/`: <logos, áudio>

| # | Dur. (s) | Tipo | Narração | Visual | Ficheiros |
|---|---|---|---|---|---|
| 1 | 3 | canvas | — | Logo da marca (`sources/logos/logo.svg`) entra com fade sobre fundo escuro | `scenes/01.html` |
| 2 | 5 | higgsfield-video | <máx. 10 palavras> | <descrição da cena> | `scenes/02.mp4`, `audio/02.mp3` |
| 3 | 4 | higgsfield-img | <máx. 8 palavras> | <imagem fixa com zoom lento> | `scenes/03.png`, `audio/03.mp3` |
| 4 | 3 | canvas | <CTA> | Logo + CTA | `scenes/04.html`, `audio/04.mp3` |

Tipos: canvas (gratuito, renderizado com `${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/render_canvas.py`) · higgsfield-img (imagem + Ken Burns na montagem) · higgsfield-video (image-to-video)
Regra: ~2 palavras por segundo de narração. Gerar a narração primeiro e ajustar a duração da cena ao áudio real.
