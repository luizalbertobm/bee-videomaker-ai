---
description: Verifica o que a skill videomaker precisa; na primeira execução num projeto, guia a preparação passo a passo
argument-hint: "[guiado | reset]"
---
Diagnóstico e preparação da skill videomaker. Argumento recebido: `$ARGUMENTS`

Começa sempre por correr, a partir da raiz do projeto:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/doctor.sh --json
```

O JSON traz `first_run` (o projeto ainda não tem `.videomaker/setup.json`), os totais em falta e uma lista `steps`, cada um com `id`, `group`, `required`, `status` (`ok`, `missing` ou `check`), `detail` (para que serve ou o que falta) e `fix` (o comando ou a ação que resolve).

Escolhe o modo:

- **Assistente guiado** se `first_run` for `true`, ou se o argumento for `guiado`, `wizard` ou `setup`.
- **Relatório rápido** nos outros casos.
- Se o argumento for `reset`, corre `doctor.sh --reset`, diz que a próxima execução volta a ser guiada e termina.

## Relatório rápido

Mostra uma tabela curta por grupo (✓ pronto, ✗ obrigatório em falta, · opcional em falta) e verifica os conectores como no passo 8 abaixo. Se faltar algo obrigatório, pergunta se o utilizador quer ser guiado só por esses itens e, se sim, segue as regras do assistente para eles. Se estiver tudo pronto, diz isso numa linha.

## Assistente guiado

Abre com duas linhas: o que vai acontecer (nove passos curtos, os que já estão prontos passam sozinhos) e quantos itens obrigatórios e opcionais faltam. Depois percorre os passos **pela ordem abaixo, um de cada vez**.

Regras para todos os passos:

- Anuncia cada passo como "Passo N de 9 — nome". Se tudo no passo já está `ok`, confirma-o numa linha e avança sem perguntar nada.
- Para cada item em falta: uma frase a dizer para que serve (usa o `detail`), depois o comando exato (usa o `fix`) num bloco `bash`, um comando por bloco.
- Antes de instalar ou criar qualquer coisa, pergunta ao utilizador (com a ferramenta de pergunta, quando existir) com estas opções: instalar agora, faço eu e aviso, saltar este passo. Num item opcional, a opção recomendada pode ser saltar.
- Comandos com `sudo`: não os corras. Mostra o bloco e pede ao utilizador para o correr no terminal dele, porque pede a palavra-passe; espera que diga que terminou.
- Comandos sem `sudo` (`pip`, `mkdir`, copiar ficheiros) podes correr tu depois do sim.
- Depois de cada passo com alterações, volta a correr `doctor.sh --json` e confirma que o item passou a `ok` antes de avançar. Se continuar em falta, mostra o erro e propõe a alternativa; não avances em silêncio.
- Um passo obrigatório saltado fica anotado para o resumo final. Nunca digas que a skill está pronta com obrigatórios em falta.
- Nunca peças chaves, tokens ou palavras-passe no chat, nem os escrevas tu em ficheiros: o utilizador edita o `.env` ele próprio.

### Passo 1 — Ferramentas do sistema (`group: sistema`)
`ffmpeg`/`ffprobe`, `bc` e `python3`. Junta os que faltam num só comando do gestor de pacotes indicado em `package_manager`.

### Passo 2 — Pacotes Python (`group: python`)
`playwright`, `numpy` e `faster-whisper` são obrigatórios; `pillow` é opcional. Junta os que faltam num só `pip install`, com as flags que o `fix` traz. Avisa que o `faster-whisper` descarrega um modelo de cerca de 3 GB na primeira transcrição, não agora. Se o pip recusar por "externally-managed-environment", propõe um ambiente virtual (`python3 -m venv .venv && source .venv/bin/activate`) em vez de forçar.

### Passo 3 — Google Chrome (`group: chrome`)
O render desenha as cenas no Chrome. Se faltar, mostra o `fix`. Alternativa sem Chrome: `python3 -m playwright install chromium` e trocar `channel="chrome"` por Chromium em `render_canvas.py`; só a proponhas se o utilizador não puder instalar o Chrome.

### Passo 4 — Pastas do projeto (`id: pastas`)
Cria as pastas em falta com o `mkdir -p` do `fix` (podes correr depois do sim). Explica numa linha: `sources/` guarda o que é da marca, `scenes/` e `audio/` o trabalho de cada vídeo, `build/` os intermediários.

### Passo 5 — Logos e fontes (`id: logos`, `id: fontes`)
Estes ficheiros são do utilizador e nunca se geram. Pergunta onde estão (um caminho no computador) e copia-os para `sources/logos/` e `sources/fonts/`. Nos logos, prefere SVG. Nas fontes, o `detail` diz que nomes de ficheiro os modelos de cena esperam: copia com esses nomes ou, se a marca usa outras fontes, diz que as cenas ajustam `FONT_FACES`. Se a marca não tiver fonte própria, sugere uma livre do Google Fonts (licença OFL) e deixa o utilizador escolher e descarregar.

### Passo 6 — Identidade visual (`id: identidade`, opcional)
Se faltar, oferece criar `sources/identidade-visual.md` a partir de três perguntas: cores (fundo, texto, acento, em hexadecimal), fonte de títulos e de corpo, e regras do logo (versões, o que evitar). Se o utilizador tiver um manual de marca em PDF, oferece resumi-lo. Pode saltar: sem o ficheiro, a paleta pergunta-se em cada briefing.

### Passo 7 — Stock gratuito (`id: pixabay`, opcional)
Sem a chave do Pixabay não há stock de vídeo. Se faltar e o utilizador a quiser:
1. Se não existir `.env`, cria-o só com a linha `PIXABAY_API_KEY=` vazia e garante que `.env` está no `.gitignore` quando o projeto é um repositório git.
2. Pede ao utilizador para abrir https://pixabay.com/api/docs/ (com sessão iniciada a chave aparece na própria página), colar a chave depois do `=` no `.env` e avisar quando estiver feito.
3. Confirma com uma pesquisa real: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/stock.py "ocean" --type video --limit 1`. Uma linha de resultado quer dizer que a chave funciona.

### Passo 8 — Conectores (`group: conectores`)
O script não os consegue ver; verifica tu nas ferramentas desta sessão:
- **ElevenLabs (obrigatório para narração e música):** procura uma ferramenta cujo nome termine em `creative_generate_speech`. Se existir, está ligado.
- **Higgsfield (opcional, imagens e vídeo gerados):** procura ferramentas que terminem em `generate_image` ou `generate_video`.

Se algum faltar, lê `${CLAUDE_PLUGIN_ROOT}/skills/videomaker/references/setup-mcp.md` e guia o utilizador pelo registo e pelo login (o login é feito por ele no browser). Diz claramente que, sem ElevenLabs, a skill ainda faz roteiro, cenas Canvas, efeitos e montagem, e pode usar narração já gravada.

### Passo 9 — Teste final
Com os obrigatórios dos passos 1 a 3 prontos, corre o teste real da cadeia, que renderiza uma cena mínima, converte um ícone, faz uma faixa de efeitos e monta o vídeo, tudo numa pasta temporária:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/doctor.sh --smoke
```

Se algum ponto falhar, mostra a mensagem de erro, volta ao passo correspondente e repete o teste depois de corrigir.

### Fecho
Quando não houver obrigatórios em falta e o teste final passar, regista a preparação, para que as próximas execuções sejam só o relatório rápido:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/doctor.sh --mark-done
```

Termina com um resumo: uma tabela dos nove passos (pronto, saltado, em falta), o que ficou por fazer e porquê, e um exemplo de primeiro pedido, como `/bee:videomaker cria um reel de 15 s a apresentar a marca`. Se ficaram obrigatórios em falta, **não** registes a preparação: diz o que falta e que basta voltar a correr `/bee:doctor` para retomar.
