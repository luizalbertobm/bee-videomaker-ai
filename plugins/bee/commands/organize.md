---
description: Migra um projeto do videomaker com o layout antigo (tudo na raiz) para a estrutura brand/, library/ e videos/<slug>/
argument-hint: "[slug do vídeo]"
---
Reorganização das pastas de um projeto da skill videomaker. Argumento recebido: `$ARGUMENTS`

A estrutura nova separa o que é partilhado do que é de cada vídeo, e a produção das entregas:

```
brand/                 logos/, fonts/, icons/, brand-guide.md
library/               stock/, sfx/, music/, credits.md
references/<id>/       análises de vídeos de terceiros
videos/<slug>/         script.md, production/{inputs,scenes,audio,build}/, deliverables/
```

1. Mostra o plano, a partir da raiz do projeto, sem mover nada:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/migrate_layout.py --json
```

   Se `moves` vier vazio, diz que o projeto já está organizado (ou não é um projeto do videomaker) e termina.

2. Apresenta ao utilizador uma tabela curta agrupada por regra (marca, produção, entregas, stock, etc.), os itens com `conflict: true` (destino já ocupado, ficam por migrar) e a lista `left_in_place` (pastas e ficheiros que o script não reconhece e não toca). Tudo o que estiver no layout antigo vira **um só vídeo**: versões antigas, roteiros `-v3`/`-v4` e MP4 finais ficam todos nesse vídeo (`script-*.md`, `deliverables/`).

3. Pergunta, com a ferramenta de pergunta ao utilizador quando existir: o nome do vídeo (sugere o `slug` do JSON, ou o argumento, se veio um) e se aplica a migração agora. Se o projeto for um repositório git com alterações por gravar, recomenda gravá-las antes, para a migração ficar num commit próprio.

4. Com o sim, aplica:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/migrate_layout.py --slug <slug> --apply
```

5. Confirma o resultado:
   - `bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/doctor.sh --json` e verifica que `layout` e `pastas` estão `ok`.
   - Abre uma cena migrada (`videos/<slug>/production/scenes/*.html`) e confirma que os caminhos de logos, fontes e ícones foram reescritos para `../../../../brand/...` (o script diz quantos reescreveu). Se houver cenas, renderiza uma para provar: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/render_canvas.py <cena>.html <pasta do build>/teste.mp4`.

6. Termina com um resumo: quantos itens mudaram de sítio, o que ficou por migrar e porquê, e sugere o que fazer com cada item de `left_in_place` (ex. uma pasta `en/` com cenas e áudio é uma variante: mover para `production/scenes/en/` e `production/audio/en/`). Não movas esses itens sem perguntar. O registo da migração fica em `.videomaker/migration.log`.
