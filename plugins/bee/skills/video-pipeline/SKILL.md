---
name: video-pipeline
description: Produz vídeos curtos de ponta a ponta para a marca do projeto — roteiro por cenas, animações em Canvas renderizadas localmente, narração com ElevenLabs, clipes gerados no Higgsfield e montagem final com ffmpeg. Usar sempre que o utilizador pedir um vídeo, animação, explainer, teaser, anúncio, reel, vídeo para redes sociais, intro/outro com logo, ou quiser juntar narração a imagens ou animações — mesmo que não diga a palavra "vídeo" (ex. "faz um reel de 15 s", "anima o logo com uma voz off"). Não usar para gerar uma única imagem ou um único áudio isolados.
---

# Video Pipeline

Fluxo para produzir um vídeo curto com o mínimo de créditos gastos: tudo o que é texto, gráfico ou logo é feito em Canvas (gratuito e renderizado localmente); só as cenas que precisam de imagem/vídeo gerado passam pelo Higgsfield, e a voz pelo ElevenLabs.

## Onde está cada coisa

Esta skill vem do plugin `bee` (invocação `/bee:video-pipeline`, diagnóstico `/bee:doctor`); os scripts e modelos vivem na pasta do plugin (`${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/`, já substituída nos comandos abaixo) e os ficheiros do projeto nas pastas da raiz do projeto. Na primeira utilização num projeto, correr o diagnóstico e criar as pastas em falta:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/doctor.sh
```

Caminhos do projeto, relativos à sua raiz:

| Pasta | Conteúdo | Quando usar |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/` | **Ferramentas executáveis** do pipeline: `render_canvas.py` (cena Canvas → MP4), `transcribe.py` (áudio → texto, SRT, VTT, JSON com timestamps por palavra, local e gratuito), `stock.py` (pesquisa e descarrega imagens, vídeos e sons gratuitos de Pexels, Pixabay e Openverse, com ficheiro de créditos), `icons.py` (ícones Lucide por nome ou pesquisa, convertidos para caminhos Canvas em `sources/icons/lucide/icons.js`) e `montagem.ffmpeg.sh` (concatena cenas, cola narração e legendas). | Sempre que for preciso renderizar uma cena, transcrever um áudio, ir buscar stock gratuito ou montar o vídeo final. Correr a partir da raiz do projeto; não reescrever. |
| `sources/` | **Ficheiros fonte** fornecidos pelo utilizador (criar se não existir): logos da marca em `sources/logos/` (SVG de preferência; PNG como alternativa), fontes `.ttf` em `sources/fonts/`, opcionalmente `sources/identidade-visual.md` com o resumo do manual da marca (cores, fontes, regras) e áudios já gravados (ex. `sources/narracao.mp3`). | Antes de gerar qualquer asset, ver se já existe aqui. Logos nunca se geram — usam-se estes. Narração existente poupa créditos ElevenLabs. |
| `${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/assets/` | Modelos: `canvas-scene.html` (esqueleto de cena com `renderFrame(t)`), `icons.js` (helper `Icons.draw` para desenhar ícones Lucide com traço a escrever-se, tile e cor), `roteiro.md` (modelo de roteiro) e as três demos de estilo `estilo-kinetic.html`, `estilo-geometrico.html`, `estilo-tech.html`. | Copiar como ponto de partida para cada cena/roteiro; a demo do estilo escolhido é o template das cenas. |
| `${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/references/` | `estilos-animacao.md` (os três estilos, quando usar cada um e a receita de cada), `licoes-aprendidas.md` (custos reais, armadilhas de formato e duração) e `setup-mcp.md` (registar Higgsfield e ElevenLabs no Claude Code). | Ler `estilos-animacao.md` na etapa 1 para apresentar os estilos; `licoes-aprendidas.md` antes de estimar custos ou gerar vídeo; `setup-mcp.md` só se os conectores não aparecerem. |
| `scenes/`, `audio/`, `build/` | Pastas de trabalho criadas durante a produção (ver convenção abaixo). | Criadas na raiz do projeto na etapa 2. |

Convenção de nomes: cena `NN` → `scenes/NN.html` (fonte Canvas) renderizada para `scenes/NN.mp4`, ou `scenes/NN.mp4|png` vindo do Higgsfield; narração `audio/NN.mp3`. O script de montagem lê **só** `scenes/NN.mp4|webm|png|jpg` e escreve os intermediários normalizados em `build/`. A numeração é o que liga vídeo e áudio.

## Pré-requisitos

- **ElevenLabs já está ligado ao Claude** como conector da app (tools `creative_*`, com um prefixo de id gerado — procurar pelo sufixo, ex. `creative_generate_speech`). É a via **padrão e obrigatória** para vozes profissionais: toda a narração nova sai daqui, nunca de TTS local ou de outro serviço. Não precisa de instalação; se as tools `creative_*` não aparecerem na sessão, pedir ao utilizador para verificar o conector em `/mcp`.
- **Higgsfield** (imagem, vídeo, upscale, reframe) também como conector; se faltar, ler `references/setup-mcp.md`.
- **Local**: `python3` com `playwright` (Python) e `faster-whisper`, Google Chrome instalado (o render usa `channel="chrome"`), `ffmpeg`/`ffprobe` e `bc`. Verificar com `ffmpeg -version` e `python3 -c "import playwright, faster_whisper"`. Instalação em `references/setup-mcp.md`.
- **Chaves de stock (opcionais, gratuitas)**: `PIXABAY_API_KEY` num ficheiro `.env` na raiz do projeto (ver `references/setup-mcp.md`); é a fonte principal de vídeo. `PEXELS_API_KEY` só se já existir: o Pexels deixou de emitir chaves novas em setembro de 2026. Sem chaves o `stock.py` só usa o Openverse (imagens e sons CC, sem vídeo).
- **Antes de qualquer operação paga**: verificar créditos (`balance` no Higgsfield) e confirmar com o utilizador duração, formato (9:16, 16:9, 1:1), idioma, tom e voz. Se o saldo for curto, propor um plano reduzido (menos cenas, modelo mais barato) em vez de avançar às cegas.

## Fluxo em 6 etapas

### 1. Briefing e roteiro

1. Recolher objetivo, público, duração, formato, idioma e referências. Inventariar `sources/` e dizer ao utilizador o que já existe (logos, áudio).
2. **Pedir ao utilizador que escolha o estilo de animação** entre os três de `references/estilos-animacao.md`, antes de escrever o roteiro, porque o estilo muda o ritmo das cenas e o texto que cabe em cada uma. Apresentar cada um numa linha, com a sugestão para o briefing em primeiro lugar, e usar a ferramenta de pergunta ao utilizador (AskUserQuestion) quando existir:
   - **Tipografia cinética**: palavras grandes ao ritmo da narração, fundos sólidos que trocam, cortes secos. Para mensagens curtas e reels rápidos.
   - **Motion graphics geométrico**: formas que se desenham e montam, cartões, favo de mel, fundo claro. Para explainers e listas.
   - **Tech escuro com brilho**: fundo quase preto, partículas, linhas de luz, contadores. Para software, métricas e lançamentos.
   Se o utilizador já descreveu um estilo próprio, usá-lo em vez destes, mas dizer qual dos três fica mais perto.
3. Copiar `assets/roteiro.md` e escrever o roteiro em cenas numeradas. Cada cena tem duração (s), narração (texto exato), visual e tipo: `canvas` | `higgsfield-img` | `higgsfield-video`.
4. Regra: **~2 palavras por segundo** de narração (o eleven_v4 lê mais devagar do que parece; 15 palavras deram 7 s). Uma cena de 5 s leva no máximo 10 palavras.
5. Apresentar o roteiro e esperar aprovação. Nada se gera antes disso — refazer roteiro é grátis, refazer vídeo não.

### 2. Cenas em Canvas (gratuitas)

Usar para títulos, logo intro/outro, lower-thirds, contadores, gráficos, diagramas, transições e CTA.

- Uma cena por ficheiro HTML autónomo em `scenes/NN.html`, copiada da demo do estilo escolhido (`${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/assets/estilo-*.html`) ou de `assets/canvas-scene.html` para cenas só com logo; os modelos referem `../sources/` relativo a `scenes/`. Seguir a receita do estilo em `references/estilos-animacao.md`: paleta, tipografia, vocabulário de movimento e tempos.
- Manter no topo as constantes `WIDTH`, `HEIGHT`, `FPS`, `DURATION_S` e uma `renderFrame(t)` **determinística** (t em segundos). O render frame a frame depende disto: cada frame é desenhado chamando `renderFrame(i/FPS)`; qualquer estado acumulado entre chamadas sai errado.
- Logos: carregar de `sources/logos/` com `new Image()` (caminho relativo a `scenes/`, ex. `../sources/logos/logo.svg`) e só começar o loop depois do `onload`. O render espera por `renderFrame` existir, por isso definir a função só depois das imagens carregarem.
- **Ícones: Lucide** (ISC, traço 2 px em base 24; conjunto consistente e compacto). Nunca desenhar ícones à mão nem gerar com modelos. Fluxo: `icons.py --search <palavra>` para achar o nome, `icons.py nome1 nome2` para descarregar (grava `sources/icons/lucide/<nome>.svg` e regenera `icons.js`), copiar o helper para o projeto uma vez (`cp ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/assets/icons.js scenes/`) e na cena `<script src="../sources/icons/lucide/icons.js">` + `<script src="icons.js">`, depois `Icons.draw(ctx, 'truck', cx, cy, 120, { progress, bg: ACCENT, color: INK })`. `progress` 0..1 faz o traço escrever-se; `bg` desenha o tile atrás; `fill: true` preenche. Catálogo com ~2.000 ícones em https://lucide.dev/icons/.
- Paleta e tipografia: se o projeto tiver `sources/identidade-visual.md`, seguir esse manual (cores oficiais, fonte de display e de corpo, regras de uso do logo). Se não tiver, pedir no briefing a paleta (2–3 cores: fundo, texto, acento) e as fontes, e gravar essa decisão no roteiro. Fontes `.ttf` em `sources/fonts/`; o template faz o `@font-face` e espera por `document.fonts`. Um acento dominante por cena; nunca recolorir, distorcer ou redesenhar o logo.
- Renderizar com o script da skill, a partir da raiz do projeto:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/render_canvas.py scenes/01.html scenes/01.mp4
```

Confirmar a saída (dimensões, duração) antes de seguir. O botão "Exportar WebM" do template é só para pré-visualização rápida no browser; a saída oficial é o MP4 do `render_canvas.py`.

### 3. Narração com ElevenLabs

1. Se `sources/` já tem a narração (ex. `sources/narracao.mp3`), **transcrevê-la primeiro** com o script da skill para saber o que diz e dimensionar as cenas pelo texto real; copiar o áudio para `audio/NN.mp3`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/transcribe.py sources/narracao.mp3 --out-dir audio
```

   É local e gratuito (faster-whisper, modelo `large-v3`; usa a GPU se houver, senão CPU). Dá a duração, o idioma, o texto e ficheiros `.txt/.srt/.vtt/.json`. Para um áudio longo em CPU, `--model small` é um rascunho rápido. Passar `--initial-prompt "Nome da Marca. Slogan da marca."` ajuda a grafar nomes próprios.
2. Caso contrário, gerar com o ElevenLabs ligado ao Claude, nesta ordem:
   - `creative_list_voices` com filtros em vez de texto solto: `languages: ["pt"]`, `use_cases: ["advertisement", "social_media"]` ou `["narrative_story"]`, `voice_category: "professional"`, e `gender`/`age`/`descriptives` conforme o briefing (ex. `["confident", "upbeat"]`). Apresentar 2–3 candidatas ao utilizador com uma linha cada e deixá-lo escolher; o resultado da geração traz um seletor de voz, por isso uma primeira escolha não é definitiva.
   - Voz à medida só se o utilizador a descrever: `creative_design_voice` com a descrição **e** a frase de teste nas palavras dele, depois `creative_save_designed_voice`.
   - `creative_create_flow` uma vez por vídeo e passar o mesmo `flow_id` em todas as chamadas.
   - `creative_generate_speech` com `estimate_only: true` primeiro para mostrar o custo; depois **uma chamada por cena**, `model_id: "eleven_v4"`, `generations_count: 1` (2 só se o utilizador quiser escolher takes), texto exato da cena. Tags de direção inline (`[pausa]`, `[entusiasmado]`) funcionam no v4. Nunca repetir uma chamada para "tentar outra vez": cada chamada cobra.
   - Esperar com `creative_get_flow_run_status` (flow_id + session_ids) até `all_completed`; obter o `full_res_url` com `creative_get_generations` e descarregar.
3. Descarregar logo cada áudio para `audio/NN.mp3` — os links expiram em horas.
4. Ler a duração real de cada áudio. Se ultrapassar a cena, encurtar o texto ou alargar a cena; gerar a narração **antes** do vídeo para dimensionar a cena pelo áudio e não o contrário.
5. Legendas: `transcribe.py audio/NN.mp3 --max-chars 24 --formats srt` gera blocos curtos com timestamps por palavra, ideais para reels; juntar os SRT das cenas (com offset) em `legendas.srt` na raiz para o script de montagem os gravar. Não gastar créditos ElevenLabs em transcrição.

### 3b. Stock gratuito antes de gerar

Para cenas de ambiente genérico (cidade, escritório, natureza, tecnologia, texturas) e para efeitos sonoros, tentar primeiro um banco gratuito; a geração paga fica para o que tem de ser à medida (produto, personagem, marca).

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/stock.py "honeycomb macro" --type video --orientation portrait --limit 8
python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/stock.py "honeycomb macro" --type video --orientation portrait --download 2 --out-dir stock
python3 ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/stock.py "whoosh transition" --type audio --download 1 --out-dir stock
```

- `--type image|video|audio`, `--orientation portrait|landscape|square`, `--min-width/--min-height` para garantir resolução, `--json` para a saída ser lida por código.
- Pesquisar em inglês: os bancos indexam em inglês. Pedir ao utilizador para escolher entre os resultados (mostrar a tabela) antes de descarregar.
- Depois de descarregar, mover/renomear para `scenes/NN.mp4|png` ou `audio/`; a imagem fixa ganha Ken Burns na montagem.
- Cada download acrescenta uma linha a `creditos.md` na raiz. Entregar esse ficheiro com o vídeo: Pexels e Pixabay pedem que se mostre a origem, e as licenças CC BY do Openverse **exigem** a atribuição que o ficheiro já traz pronta. Preferir CC0 quando houver.
- O Openverse responde 502/504 de vez em quando; o script repete 3 vezes. Se continuar, usar só `--source pixabay`.

### 4. Visuais com Higgsfield

- Imagens-chave com `generate_image` (ou `generate_image_batch` para várias cenas). Prompt = visual da cena + estilo global. O formato vai **sempre** no parâmetro `aspect_ratio`, nunca só no texto — o modelo ignora "9:16" escrito no prompt.
- Vídeo com `generate_video` a partir da imagem aprovada (image-to-video), duração = duração da cena; `generate_video_batch` para o lote. Esperar com `jobs_wait`, ver com `show_result`.
- Estimar antes com `estimate_only`/`get_cost`. Modelos: mini para testes, Seedance 2.5 para entregas (custos em `references/licoes-aprendidas.md`).
- Gerar **uma** cena de teste, validar o estilo com o utilizador, só depois o lote.
- Confirmar `width`/`height` no resultado. Se vier no formato errado, `reframe` ou o `pad` do ffmpeg — não regenerar.
- Guardar em `scenes/NN.mp4` ou `scenes/NN.png`. O Seedance gera áudio próprio; o script de montagem descarta-o e usa só a narração.

### 5. Montagem

Entregar ao utilizador uma tabela: cena, ficheiro visual, ficheiro áudio, início, fim, transição. Depois correr o script da skill a partir da raiz do projeto:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/video-pipeline/scripts/montagem.ffmpeg.sh video-final.mp4
```

O script normaliza cada cena para o mesmo formato (padding, fps), cola `audio/NN.mp3` quando existir, aplica Ken Burns a imagens fixas pela duração do áudio, concatena e grava `legendas.srt` se existir. Formato e fps ajustam-se por variável de ambiente (`W`, `H`, `FPS`).

### 6. Revisão

Perguntar sobre ritmo, voz, estilo visual e texto. Regenerar só as cenas alteradas (nunca o vídeo inteiro) e voltar a correr a montagem — é por isso que cada cena vive no seu próprio ficheiro.

## Regras

- Nenhuma operação paga sem roteiro aprovado e créditos verificados.
- Uma cena de teste antes do lote.
- Canvas para tudo o que for texto, gráfico, logo ou diagrama: é grátis, determinístico e editável.
- Stock gratuito (`stock.py`) antes de geração paga para cenas genéricas e efeitos sonoros; créditos sempre em `creditos.md`.
- Logos vêm de `sources/logos/`; nunca pedir a um modelo para desenhar o logo.
- Manter um bloco `## Assets` na conversa com IDs de jobs, `flow_id`, URLs e caminhos locais, para reutilização na revisão.
- Se um conector falhar, continuar com as etapas restantes (Canvas e montagem funcionam offline) e dizer claramente o que ficou em falta.
