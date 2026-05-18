# Zen Stack Spec

Escolhas técnicas claras, sem ambiguidade. Stack Spec diz **com o quê**; Eng Spec diz **a estrutura**; ZenSpec diz **o comportamento**; código diz **como**.

---

## Objetivo

Produzir documentos de stack:

- **Determinísticos** — Cada escolha tem alternativa descartada e motivo.

- **Reproduzíveis** — Qualquer dev ou agente monta o ambiente seguindo só isto.

- **Navegáveis** — Tabela de decisões encontrável em 5 segundos.

- **Compatíveis com IA e com equipes** — Formato que qualquer pessoa ou modelo consiga seguir.

---

## Fonte da Verdade

Este documento é a única fonte válida das escolhas técnicas do projeto.

Se houver divergência entre o que está instalado e este documento, o documento prevalece.

Cadeia: **Conceito → Engenharia → Stack → ZenSpec → Código**.

---

## Princípios

- **O que está aqui é o sistema. O que não está, não existe.**

- **Duas linhas por explicação.** Se precisar de mais, a decisão não está clara.

- **Toda escolha tem dono.** Responde a uma necessidade do conceito ou da engenharia. Se não responde a nada → não precisa estar aqui.

- **Alternativa obrigatória.** Sem alternativa real → é restrição, não decisão. Mover pra Restrições.

- **Motivo em uma frase.** "Porque é popular" não é motivo.

- **Restrições ≠ decisões.** Restrição é o que o ambiente impõe. Decisão é o que você escolhe dentro.

- **Versões quando importa.** Registrar se importa. `"latest"` se qualquer recente serve.

- **Legível sozinha.** Sem conhecimento oral do projeto.

---

## Formato

### Seções

| # | Seção | O que contém |
| - | ----- | ------------ |
| 1 | **Intenção** | Uma frase: "Esta stack existe para que **[quem]** consiga **[construir/rodar/testar o quê]** sem precisar de **[o quê]**." |
| 2 | **Restrições** | Tabela `Restrição / Imposta por / Consequência`. O que o ambiente impõe, não o que você escolhe. Se mudar aqui, decisões caem. |
| 3 | **Decisões** | Tabela `Categoria / Decisão / Alternativa descartada / Motivo`. Categorias livres (linguagem, build, testes, qualidade, observabilidade, CI/CD, etc.). |
| 4 | **Dependências** | Tabela `Pacote / Versão / Papel / Dev-only?`. Zero dependências sem justificativa. |
| 5 | **Scripts** | Tabela `Comando / O que faz`. Tudo que o dev precisa pra clonar e rodar. |
| 6 | **Pastas** | Árvore de primeiro e segundo nível. Código fala por si depois disso. |
| 7 | **Escopo fora** | O que deliberadamente não usamos e por quê (uma frase cada). |

Se não se aplica → "Não se aplica." Nunca omitir.

---

## Regras visuais

- **Tabelas > parágrafos.** Sempre.

- **Uma decisão = uma linha.**

- **Nomes de pacotes em `código`.** Sem variação.

---

## Antes de escrever

- Restrições vindas do conceito ou da engenharia?
- Decisões orais não registradas?
- Dependências sem justificativa?
- Comandos que "todo mundo sabe" mas não estão escritos?

Se não sabe → perguntar. Se sabe → definir.

---

## Depois de escrever

- Toda escolha tem alternativa e motivo?
- Toda restrição separada das decisões?
- Toda dependência com papel claro?
- Todo comando necessário listado?
- Pastas refletem o repo?
- Alguém clona e roda seguindo só isto?
- Dá pra escrever ZenSpecs com essa stack sem perguntar nada?
