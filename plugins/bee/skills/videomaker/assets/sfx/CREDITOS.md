# Biblioteca de efeitos sonoros da skill

Sons curtos e gratuitos (todos **CC0 1.0**, domínio público) para `sfx_track.py`, em duas partes:

1. **Sons base** (esta pasta): nove sons do Freesound via Openverse, com nome curto (`pop`, `whoosh`…), escolhidos a dedo para reels.
2. **Pacote Kenney "Interface Sounds"** (`kenney-interface/`): 100 sons de interface em 20 famílias com variações numeradas, pensados para UI e motion graphics.

Ficam aqui para não ser preciso voltar a descarregá-los: a folha de deixas refere-os pelo nome, sem extensão nem pasta
(`pop`, `maximize_005`); o script procura nas subpastas. Um som novo descarregado com `stock.py --type audio` pode ser
acrescentado a esta pasta com um nome curto e uma linha na tabela dos sons base.

## Sons base

| Nome | Para quê | Original | Autor | Licença | Página |
|---|---|---|---|---|---|
| `whoosh` | entrada, saída ou movimento de um objeto grande (0,3–0,5 s, sobe e desce) | Space Swoosh - brighter | GameAudio | CC0 1.0 | https://freesound.org/people/GameAudio/sounds/220191 |
| `swish` | troca de bloco ou cartão que entra (ar, 0,15 s) | Swosh swoosh whoosh air sound, free, high quality | qubodup | CC0 1.0 | https://freesound.org/people/qubodup/sounds/60026 |
| `riser` | algo a subir ou a crescer até um ponto (pico no fim, 0,3 s) | Backwards Whoosh | SlavicMagic | CC0 1.0 | https://freesound.org/people/SlavicMagic/sounds/446010 |
| `click` | toque num botão (seco, 20 ms) | UI Button Click | benzix2 | CC0 1.0 | https://freesound.org/people/benzix2/sounds/467951 |
| `tick` | linhas de lista, texto a ser escrito (muito curto e suave) | Soft UI Button Click | Jummit | CC0 1.0 | https://freesound.org/people/Jummit/sounds/528561 |
| `pop` | ícones, etiquetas e selos que surgem; subir o pitch em séries | The Best Bubble Pop Sound For Game and UI | el_boss | CC0 1.0 | https://freesound.org/people/el_boss/sounds/669918 |
| `pop-soft` | mensagens de chat, notificações (mais redondo e grave) | Pop 2 | greenvwbeetle | CC0 1.0 | https://freesound.org/people/greenvwbeetle/sounds/244654 |
| `glock` | nota de glockenspiel (fá 4): confirmação; pitch 1.5 + 2.0 seguidos dá "aprovado" | Glockenspiel_46_f4_04 | cabled_mess | CC0 1.0 | https://freesound.org/people/cabled_mess/sounds/348924 |
| `shimmer` | brilho contínuo de 5 s; usar uma fatia (inicio duracao) sob logos e botões | Shimmery.wav | opticaillusions | CC0 1.0 | https://freesound.org/people/opticaillusions/sounds/521886 |

## Pacote Kenney "Interface Sounds" (`kenney-interface/`)

**Interface Sounds 1.0** · Kenney (www.kenney.nl) · **CC0 1.0** (crédito opcional, mas apreciado: "Sons de interface por Kenney") · licença original em `kenney-interface/LICENSE.txt` · página: https://kenney.nl/assets/interface-sounds

Formato OGG Vorbis, mono, muito curtos (a maioria 0,05–0,5 s). As variações (`_001`, `_002`…) são o mesmo gesto com timbre ou altura diferente: numa série (lista, ícones, barras) alternar variações soa mais natural do que repetir a mesma com `pitch`.

| Família | Quantos | Duração | Para quê (na animação) | Pico sugerido |
|---|---|---|---|---|
| `click_001…005` | 5 | 0,01–0,10 s | toque num botão, cursor que carrega, letra a aparecer | −14 dB |
| `tick_001/002/004` | 3 | 0,02–0,05 s | texto a ser escrito, linhas de lista, contador a correr | −25 dB |
| `select_001…008` | 8 | 0,04–1,9 s | destaque de um item, foco num cartão (001–005 secos; 006–008 longos, com cauda) | −20 dB |
| `toggle_001…004` | 4 | 0,07–0,14 s | interruptor, caixa de verificação, ícone que troca de estado | −16 dB |
| `switch_001…007` | 7 | 0,50–0,62 s | mudança de modo ou de ecrã, troca de separador | −18 dB |
| `open_001…004` / `close_001…004` | 4+4 | 0,15–0,32 s | painel, menu ou janela que abre / fecha (sobe / desce) | −18 dB |
| `maximize_001…009` / `minimize_001…009` | 9+9 | 0,19–0,53 s | cartão que cresce ou entra em cena / encolhe ou sai; ótimos para "whoosh" de UI | −18 dB |
| `drop_001…004` | 4 | 0,11–0,29 s | objeto que cai ou pousa, ícone que assenta num tile | −16 dB |
| `confirmation_001…004` | 4 | 0,29–0,54 s | tarefa concluída, visto verde, CTA que aparece (duas notas a subir) | −18 dB |
| `pluck_001/002` | 2 | 0,10–0,16 s | corda beliscada: ponto de lista, etiqueta de preço | −20 dB |
| `glass_001…006` | 6 | 0,11–0,69 s | brilho de vidro: logo, selo, notificação suave | −20 dB |
| `bong_001` | 1 | 0,12 s | sino grave e curto: fecho de secção | −18 dB |
| `question_001…004` | 4 | 0,33–0,49 s | pergunta no ecrã, dúvida, balão "?" (duas notas a subir, em suspenso) | −18 dB |
| `error_001…008` | 8 | 0,10–0,53 s | problema, "antes" num antes/depois, cruz vermelha (graves, a descer) | −18 dB |
| `back_001…004` | 4 | 0,06–0,09 s | voltar atrás, anular, elemento que recua | −18 dB |
| `scroll_001…005` | 5 | 1,0 s | lista a deslizar, feed a passar (usar fatia `inicio duracao` para encurtar) | −22 dB |
| `glitch_001…004` | 4 | 0,01–0,03 s | falha digital, texto a tremer, estilo tech | −20 dB |
| `scratch_001…005` | 5 | 0,12–0,33 s | riscar, apagar, rasgar; transição brusca | −18 dB |

Exemplo de folha de deixas que mistura as duas partes:

```
# tempo  som               pico  pitch
0.40     whoosh            -16
1.20     maximize_005      -18          # cartão entra
1.95     click_002         -14          # toque no botão
2.30     confirmation_002  -18          # visto verde
3.00     tick_001          -25
3.08     tick_002          -25
3.16     tick_004          -25          # texto a escrever-se, variações alternadas
```

Outros pacotes CC0 do Kenney que podem ser acrescentados da mesma forma (uma subpasta + uma secção aqui): "UI Audio" (cliques e rollovers), "Digital Audio" (power-ups, tons e risers eletrónicos, bons para o estilo tech), "Impact Sounds" (impactos de materiais).
