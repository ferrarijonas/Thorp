# Zen Eng Spec

Arquitetura clara, sem ambiguidade. Eng Spec diz **a estrutura**; ZenSpec diz **o comportamento**; código diz **como**.

---

## Objetivo

Produzir documentos de engenharia/arquitetura que sejam:

- **Determinísticos** — Se X → Y. Sem "talvez", "pode ser", "idealmente".

- **Navegáveis** — Qualquer seção encontrável em 5 segundos. Tabelas > parágrafos.

- **Deriváveis** — De cada componente descrito aqui, uma ZenSpec completa deve poder ser escrita sem inventar nada.

- **Compatíveis com IA e com equipes** — Formato que qualquer pessoa ou modelo consiga ler, seguir e auditar.

---

## Fonte da Verdade

Este documento é a única fonte válida da arquitetura do sistema.

Se houver divergência entre código e engenharia, a engenharia prevalece.

Se houver divergência entre engenharia e conceito, o conceito prevalece.

Cadeia: **Conceito → Engenharia → ZenSpec → Código**.

Alterações na arquitetura exigem alteração prévia aqui.

---

## Princípios

### Herdados do ZenSpec (mesma filosofia)

- **O que está aqui é o sistema. O que não está, não existe.**

- **Duas linhas por explicação.** Se precisar de mais, o conceito não está claro.

- **Falha explícita.** Nunca silêncio, nunca sucesso parcial.

- **Proibições:** Não inventar componentes. Não aceitar ambiguidade. Não deixar ator implícito.

- **Escopo fora.** Lista curta do que o documento não cobre.

- **Legível sozinha.** Compreensível sem conhecimento oral do projeto.

### Específicos de engenharia

- **Glossário obrigatório.** Todo termo técnico que possa ter dois sentidos ganha uma linha de definição. Definido uma vez, usado sempre igual.

- **Componentes > Features.** Na engenharia, a unidade é o componente (programa, módulo, serviço), não a feature de usuário.

- **Contratos resumidos, não completos.** Entrada e saída com tipo e formato geral. O detalhamento campo-a-campo fica na ZenSpec de cada componente.

- **Ciclo de vida explícito.** Se o sistema tem estados (conectado, desconectado, etc.), um diagrama de estados é obrigatório.

- **Decisões registradas.** Toda escolha arquitetural que teve alternativa descartada carrega: `Decisão: X. Alternativa descartada: Y. Motivo: Z.` Uma linha.

- **Composição explícita.** Como os componentes se conectam (composição funcional, herança, injeção, etc.) em uma seção dedicada. Sem "eles se comunicam de algum jeito".

- **Idempotência e efeito.** Para cada ponto de entrada público: uma linha dizendo o que acontece se chamado duas vezes.

- **Distribuição.** Como o sistema chega na mão de quem usa. Formatos, jornadas, pré-requisitos.

---

## Formato

### Seções obrigatórias

Toda Eng Spec deve ter estas seções, nesta ordem. Se uma seção não se aplica, escrever "Não se aplica" — nunca omitir.

#### 1. Intenção

Uma frase no formato:

> Esta arquitetura existe para que **[quem]** consiga **[fazer o quê]** sem precisar de **[o quê]**.

#### 2. Glossário

| Termo  | Definição  |
| ------ | ---------- |
| `nome` | Uma frase. |

Regra: se o termo aparece mais de uma vez no documento e alguém de fora poderia interpretar diferente → vai no glossário.

#### 3. Componentes

Para cada componente:

- Nome em `código`.
- Metáfora em **negrito** (uma palavra: o garimpeiro, o tradutor, a vitrine).
- 1–2 frases do que faz.
- Contrato resumido: `Entrada: tipo. Saída: tipo.`

Regra: se um componente é orquestrador, marcar explicitamente. Adicionar uma linha de idempotência se for ponto de entrada público.

#### 4. Fluxo

**Linha do fluxo:**

```
origem → componente1 → componente2 → destino
```

**Tabela imediata abaixo:**

| Componente | Recebe | Faz  | Manda para   |
| ---------- | ------ | ---- | ------------ |
| `nome`     | tipo   | ação | próximo ou — |

Regra: toda seta do diagrama deve aparecer na tabela. Sem atalhos.

#### 5. Ciclo de vida

**Diagrama de estados:**

```
[estado1] → [estado2] → [estado3]
```

**Tabela de fases:**

| Estado | O que acontece | Se falhar |
| ------ | -------------- | --------- |

Regra: toda transição de estado tem exatamente um gatilho. Se não tem gatilho explícito, o estado não existe.

#### 6. API pública

Para cada ponto de contato com o mundo exterior:

- Nome em `código`.
- O que faz (uma frase).
- Grupo: Nuclear / Opcional / Lifecycle.
- Idempotência (uma linha).

Se houver EventEmitter: contrato de assinatura (`on/off`, retorno, payload).

#### 7. Modelo de erros

**Tabela:**

| Situação | Comportamento |
| -------- | ------------- |

Regra: toda situação de erro listada deve ser rastreável a um componente ou estado do ciclo de vida.

#### 8. Decisões e alternativas descartadas

Formato por decisão:

> **Decisão:** X.
> **Alternativa descartada:** Y.
> **Motivo:** Z.

Regra: só registrar decisões que tiveram alternativa real considerada. Não inflar com decisões óbvias.

#### 9. Distribuição e uso

- Formatos de entrega (ESM, CJS, IIFE, etc.).
- Jornada mínima do usuário (do `npm install` ao "Hello World").
- Pré-requisitos e restrições de ambiente.

#### 10. Escopo fora

Lista curta do que este documento **não** cobre.

### Seções opcionais

Usar somente quando relevante:

- **Composição interna** — se a relação entre componentes não for óbvia pelo fluxo.
- **Recuperação e invalidação** — se o sistema tem estados degradados.
- **Riscos conhecidos** — riscos técnicos com probabilidade e impacto.

---

## Regras visuais

- **Tabelas > parágrafos.** Se a informação tem estrutura repetitiva, vai em tabela.

- **Diagramas em texto.** `[estado] → [estado]` ou `origem → etapa → destino`. Sem ferramentas externas obrigatórias.

- **Metáforas permitidas, jargão não.** Se um conceito precisa de explicação, usar metáfora curta entre parênteses ou em negrito. Nunca jargão sem definição.

- **Nomes de componentes sempre em `código`.** Em tabelas, fluxos e texto. Consistente, sem variação.

- **Uma regra = uma linha.** Formato "Se X → Y" quando for regra de comportamento ou decisão.

---

## Antes de escrever (Clarificação)

Identificar antes de começar:

- Termos que podem ter dois sentidos → glossário.
- Componentes mencionados que não têm seção → criar ou remover.
- Estados do sistema que não têm transição definida → definir ou remover.
- Decisões arquiteturais tomadas oralmente mas não registradas → registrar.

Se algo não pode ser determinado → perguntar. Se pode ser definido agora → definir.

---

## Depois de escrever (Integridade)

- Todo componente mencionado no texto tem seção em Componentes?
- Todo componente aparece no Fluxo (diagrama + tabela)?
- Todo estado do Ciclo de vida tem transição com gatilho explícito?
- Toda decisão com alternativa descartada está registrada?
- Todo ponto da API pública tem grupo (Nuclear/Opcional/Lifecycle) e idempotência?
- Todo erro do Modelo de erros é rastreável a um componente ou estado?
- Nenhum termo técnico aparece sem estar no Glossário?
- Nenhum componente aparece como ator ativo no texto sem ter seção própria?
- O Escopo fora está explícito?
- É possível derivar uma ZenSpec por componente **sem inventar nada** que não esteja aqui?
- Alguém que não participou das discussões orais consegue entender a arquitetura inteira lendo só este documento?
