---
description: Verifica as dependências locais do videomaker e diz o que falta instalar
---
Corre o diagnóstico da skill videomaker e apresenta ao utilizador o que está OK e o que falta, com o comando de instalação de cada item em falta:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/doctor.sh
```

Se faltarem pastas do projeto (`sources/logos`, `sources/fonts`), pergunta ao utilizador onde estão os logos e as fontes da marca antes de as criar.
