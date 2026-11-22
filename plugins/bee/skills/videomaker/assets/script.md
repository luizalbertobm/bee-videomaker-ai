# Roteiro — <título do vídeo>

- Objetivo:
- Público:
- Duração total: <s>
- Formato: 9:16 | 16:9 | 1:1
- Idioma / voz:
- Estilo visual (paleta, tipografia, referências): <cores de brand/brand-guide.md ou do briefing; fonte de display e de corpo>
- Material disponível: <logos em brand/logos/, áudio ou capturas em production/inputs/>
- Referência de ritmo: <references/<id>/ficha.md ou "nenhuma">

Caminhos relativos a esta pasta (`videos/<slug>/`).

| # | Dur. (s) | Tipo | Narração | Visual | Ficheiros |
|---|---|---|---|---|---|
| 1 | 3 | canvas | — | Logo da marca (`brand/logos/logo.svg`) entra com fade sobre fundo escuro | `production/scenes/01.html` |
| 2 | 5 | higgsfield-video | <máx. 10 palavras> | <descrição da cena> | `production/scenes/02.mp4`, `production/audio/02.mp3` |
| 3 | 4 | higgsfield-img | <máx. 8 palavras> | <imagem fixa com zoom lento> | `production/scenes/03.png`, `production/audio/03.mp3` |
| 4 | 3 | canvas | <CTA> | Logo + CTA | `production/scenes/04.html`, `production/audio/04.mp3` |

Tipos: canvas (gratuito, renderizado com `${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/render_canvas.py`) · higgsfield-img (imagem + Ken Burns na montagem) · higgsfield-video (image-to-video)
Regra: ~2 palavras por segundo de narração. Gerar a narração primeiro e ajustar a duração da cena ao áudio real.

## Entregas

| Versão | Ficheiro (`deliverables/`) | O que mudou |
|---|---|---|
| v1 | `<slug>-v1.mp4` | primeira montagem |
