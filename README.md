# bee-video-pipeline

Plugin para Claude Code que produz reels e vídeos curtos de ponta a ponta, gastando o mínimo de créditos:

- **Roteiro por cenas** com aprovação antes de qualquer operação paga.
- **Cenas em Canvas** renderizadas localmente (Chrome headless + ffmpeg), em três estilos prontos: tipografia cinética, motion graphics geométrico e tech escuro com brilho. Ícones [Lucide](https://lucide.dev) com traço que se desenha; logo em SVG animado por camadas.
- **Narração e música** pelo conector ElevenLabs ligado ao Claude; **transcrição local** gratuita com faster-whisper (legendas por palavra).
- **Stock gratuito** (Pixabay, Pexels, Openverse) com ficheiro de créditos automático.
- **Montagem ffmpeg** com normalização, música de fundo com ducking e legendas.

Invoca-se com `/bee:video-pipeline` (ou basta pedir um vídeo); `/bee:doctor` verifica as dependências.

## Instalar

```bash
claude plugin marketplace add luizalbertobm/bee-video-pipeline
claude plugin install bee@bee-plugins --scope project   # ou --scope user
```

Depois, no projeto: `/bee:doctor`.

## O que o projeto precisa

- `sources/logos/` com os logos da marca (SVG de preferência) e `sources/fonts/` com as fontes `.ttf` (`display.ttf`, `body.ttf`, ou ajustar `FONT_FACES` nos modelos).
- Opcional: `sources/identidade-visual.md` com o resumo do manual da marca; `.env` com `PIXABAY_API_KEY` para stock de vídeo.
- Conector ElevenLabs ligado ao Claude (tools `creative_*`); Higgsfield opcional para imagens e vídeo gerados.
- Localmente: ffmpeg, bc, Python 3 com `playwright`, `faster-whisper` e `pillow`, Google Chrome.

## Estrutura

```
.claude-plugin/marketplace.json
plugins/bee/
  .claude-plugin/plugin.json, icon.png
  commands/doctor.md
  skills/video-pipeline/
    SKILL.md            fluxo em 6 etapas, regras, onde está cada coisa
    assets/             template de cena, 3 demos de estilo, helper de ícones, modelo de roteiro
    references/         estilos de animação, lições aprendidas, setup dos conectores e chaves
    scripts/            render_canvas.py, transcribe.py, stock.py, icons.py, montagem.ffmpeg.sh, doctor.sh
```

## Licença

MIT. Os ícones Lucide são ISC; os bancos de stock têm as licenças indicadas em `creditos.md` por asset.
