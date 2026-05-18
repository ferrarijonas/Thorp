# Zen Concept Spec

O que o sistema é, pra quem, e onde começa e termina. Concept Spec diz **o porquê**; Eng Spec diz **a estrutura**; Stack Spec diz **com o quê**; ZenSpec diz **o comportamento**; código diz **como**.

---

## Objetivo

Produzir conceitos:

- **Claros** — Compreensível em 30 segundos.

- **Delimitados** — Tão claro no que **não é** quanto no que é.

- **Deriváveis** — Quem lê consegue iniciar a Eng Spec sem perguntar nada.

- **Compatíveis com IA e com equipes** — Formato que qualquer pessoa ou modelo consiga seguir.

---

## Fonte da Verdade

Este documento é a única fonte válida do que o sistema é e faz.

Se houver divergência entre qualquer outro documento e o conceito, o conceito prevalece.

Cadeia: **Conceito → Engenharia → Stack → ZenSpec → Código**.

---

## Princípios

- **Uma frase deve bastar.** Se não consegue explicar o sistema em uma frase, o conceito não está claro.

- **Fronteiras > features.** Dizer o que não é evita mais problemas do que listar o que é.

- **Promessas, não implementação.** O conceito fala de valor. Nunca de código, arquitetura ou stack.

- **Metáforas bem-vindas.** O conceito é o documento mais humano da cadeia.

- **Legível sozinho.** Sem conhecimento oral do projeto.

---

## Formato

### Seções

| # | Seção | O que contém |
| - | ----- | ------------ |
| 1 | **Intenção** | Uma frase: "Este sistema existe para que **[quem]** consiga **[o quê]** sem precisar de **[o quê]**." |
| 2 | **O que é** | 1–3 frases. O que faz, onde mora, uma metáfora se ajudar. |
| 3 | **Para quem é (e não é)** | Público-alvo + contra-público em 1–2 linhas. |
| 4 | **Problema** | Dores concretas que existem hoje. Se for pioneiro, descrever a oportunidade. |
| 5 | **Diferencial** | O que faz que ninguém mais faz. Tabela comparativa se houver alternativas. |
| 6 | **Promessas** | O que o sistema entrega. Sem API, só valor. Escopo inicial vs futuro se houver. |
| 7 | **Princípios** | Regras que guiam decisões. "**Negrito.** Explicação curta." |
| 8 | **Fronteiras** | O que o sistema **não é** + o que **não cobre**. Tudo junto, sem repetir. |
| 9 | **Decisões** | "X → porque Y." Só conceituais. Arquitetura → Eng Spec. Stack → Stack Spec. |

Se não se aplica → "Não se aplica." Nunca omitir.

### Seções opcionais

- **Mapa de contexto** — `[Ator] → [Sistema] → [Ator]`. Quando há múltiplos atores externos.
- **Origem** — De onde veio. 2–3 frases.
- **Nome** — Por que se chama assim.

---

## Regras visuais

- **Tabelas para comparações.** Listas para promessas e exclusões.

- **Diagramas em texto.** Sem ferramentas externas.

- **Metáforas em negrito.** Curtas, nunca forçadas.

- **Nomes do sistema em `código`** quando for pacote/módulo.

---

## Antes de escrever

- O sistema cabe em uma frase?
- Quem é e quem não é público-alvo?
- As fronteiras estão definidas?
- As promessas são de valor, não de implementação?

Se não sabe → perguntar. Se sabe → definir.

---

## Depois de escrever

- Compreensível em 30 segundos?
- Fronteiras tão claras quanto promessas?
- Contra-público explícito?
- Zero arquitetura ou stack vazou pra dentro?
- Dá pra iniciar a Eng Spec sem inventar nada?
