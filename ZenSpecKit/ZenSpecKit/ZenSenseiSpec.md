# Zen Sensei Spec

Ordem de execução clara, em camadas. Sensei Spec diz **em que ordem** transformar Conceito, Engenharia e Stack em ZenSpecs de código, testes e código pronto.

---

## Objetivo

Produzir planos de execução:

- **Determinísticos** — Se você começar na primeira tarefa e seguir até o fim, o sistema nasce inteiro.

- **Navegáveis** — Em 5 segundos você sabe em que fase está e qual é a próxima.

- **Deriváveis** — Cada tarefa nasce de algo já definido em Concept, Eng ou Stack.

- **Compatíveis com IA e com equipes** — Cada linha pode virar issue, tarefa ou comando para um agente.

---

## Fonte da Verdade

Este documento é a única fonte válida da **ordem de trabalho** do projeto.

Se houver divergência entre este plano e qualquer outro cronograma, o Sensei Spec prevalece.

Cadeia (ida): **Conceito → Engenharia → Stack → Sensei → ZenSpec → Código**.
Produção pode acionar revisão na direção inversa — detalhes na seção "Ciclo de vida do Sensei" abaixo.

---

## Ciclo de vida do Sensei

A cadeia não é só ida. Produção pode mandar mudanças de volta:

```
Conceito <-> Engenharia <-> Stack <-> Sensei <-> Tarefas <-> Código
```

### Gatilhos de replanejamento

Quando algo inesperado surge na produção, responda estas 3 perguntas:

| Pergunta                                  | Se sim…                                                              |
| ----------------------------------------- | -------------------------------------------------------------------- |
| Muda critério de pronto de uma fase?      | Revisar `./<nome>-sensei.md` (fases + tarefas macro).               |
| Muda componentes, fluxo ou API?           | Atualizar `./<nome>-engineering.md` antes, depois revisar Sensei.              |
| Muda stack, pastas ou builds?             | Atualizar `./<nome>-stack.md` antes, depois revisar Sensei.                   |

Se **nenhum** muda: resolver como tarefa normal em `./<nome>-tarefas.md` (sem replanejamento macro).

### Ritual de replanejamento

1. Capturar a descoberta em `./<nome>-tarefas.md` com tag `#urgente`.
2. Responder as 3 perguntas de triage acima.
3. Atualizar Concept/Eng/Stack afetados.
4. Revisar `./<nome>-sensei.md`: componentes, fases, critérios de pronto, tabela de tarefas macro.
5. Registrar a mudança na seção "Registro de mudanças" do `./<nome>-sensei.md`.
6. Rederivar o "Agora (Top 10)" em `./<nome>-tarefas.md`, **mantendo em cada item a dupla linha**: apelido/entrega humana na primeira linha e `↳` técnica na segunda (ver §6.3).

---

## Princípios

- **Sem tarefa órfã.** Toda tarefa aponta para uma origem (Concept, Eng ou Stack) e uma saída concreta (arquivo, teste, código).

- **Duas escalas, não uma.** Um plano macro (fases) e uma lista micro (tarefas do dia).

- **Uma linha = uma unidade de trabalho.** Cabe numa issue, num card ou num bloco de execução da IA. No arquivo micro (`*-tarefas.md`), essa unidade pode ser um **bloco de duas linhas**: a primeira é a entrega em linguagem humana; a segunda, prefixada por `↳`, fecha o contrato técnico (programa, arquivo, critério).

- **Fases finitas.** Cada fase termina com um estado claro do projeto.

- **Dependências explícitas.** Nada depende “implicitamente” de algo que não está na tabela.

- **Paralelismo controlado.** Marcar o que pode rodar em paralelo, não assumir.

- **Legível num relance.** Tabelas primeiro, texto só para amarrar.

- **Modo de execução explícito.** Cada Sensei escolhe e declara logo no início se está em modo `Core-first` ou `UI-first/Vertical slice`, desde que Concept, Eng e Stack já estejam claros o bastante.
- **UI-first com casca e mocks é válido.** Em modo `UI-first/Vertical slice`, é aceitável começar por uma casca de UI com dados mockados como primeira fase, desde que os mocks sejam marcados como provisórios nas ZenSpecs e no próprio Sensei.

- **Plano vivo, não congelado.** O Sensei é revisado sempre que a produção revelar algo que mude fases, componentes ou critérios de pronto. Mudar o plano não é falha; falha é fingir que nada mudou.

---

## Formato

### 1. Entradas

Quais arquivos alimentam este Sensei.

| Tipo       | Arquivo                   | Papel                                           |
| ---------- | ------------------------- | ----------------------------------------------- |
| Conceito   | `./<nome>-concept.md`     | Define o porquê, o que é e fronteiras           |
| Engenharia | `./<nome>-engineering.md` | Define componentes, fluxos, ciclo de vida e API |
| Stack      | `./<nome>-stack.md`       | Define ferramentas, pastas e comandos           |

Se algum não existir ainda → escrever “Não se aplica.” e explicar em uma frase.

Logo abaixo do título principal do Sensei de um projeto real, escreva uma linha como:

- `Modo de execução: Core-first`
- `Modo de execução: UI-first/Vertical slice`

Use `Core-first` quando o projeto for mais “núcleo de lógica” (ex.: libs puras, serviços internos) e `UI-first/Vertical slice` quando a experiência visual ou o fluxo ponta-a-ponta mandarem mais que o kernel em si (ex.: painéis, ferramentas com muita interação de tela).

---

### 2. Saídas

O Sensei gera **dois arquivos**, em escalas diferentes:

| Nome           | Arquivo                    | Escala  | O que contém                         |
| -------------- | -------------------------- | ------- | ------------------------------------ |
| Sensei (macro) | `./<nome>-sensei.md`       | Macro   | Fases, componentes e grandes blocos  |
| ZenTarefas     | `./<nome>-tarefas.md`      | Micro   | Lista mínima de tarefas acionáveis   |

Regra: o Sensei (macro) é lido poucas vezes. O ZenTarefas é lido todo dia.

---

### 3. Componentes-alvo (macro)

Lista de **unidades técnicas** que vão ganhar ZenSpec + implementação.

| Nome                  | Tipo         | Fonte principal                          | Depende de                       |
| --------------------- | ------------ | ---------------------------------------- | -------------------------------- |
| `ExemploKernel`       | Componente   | Engenharia / Componentes                 | —                                |
| `ExemploClient`       | Componente   | Engenharia / Componentes                 | `ExemploKernel`                  |
| `ExemploOrchestrator` | Orquestrador | Engenharia / Componentes + Ciclo de vida | `ExemploKernel`, `ExemploClient` |

Regra geral:

- **Nome** em `código`.
- **Tipo**: Componente, Orquestrador, Infra, UI, etc.
- **Fonte principal**: onde está descrito (seção do Eng/Concept/Stack).
- **Depende de**: nomes em `código` de outras linhas.

Você pode misturar componentes de UI e de core na mesma tabela — por exemplo, um `ExemploPainelUI` lado a lado com `ExemploKernel` — desde que fique claro o tipo de cada um.

---

### 4. Fases (macro)

Quebrar o projeto em **fases de trabalho**, de alto nível.

As tabelas abaixo são exemplos de como isso pode ficar em modos diferentes. Adapte os nomes e critérios ao seu projeto.

#### Exemplo de Fases (Core-first)

| Fase | Objetivo                         | Critério de “pronto”                                                     |
| ---- | -------------------------------- | ------------------------------------------------------------------------ |
| 1    | Fundar os componentes base       | Todos os componentes de base têm ZenSpec, código e testes passando       |
| 2    | Subir orquestração e API pública | Pontos de entrada expõem o que a Eng Spec promete, com testes básicos    |
| 3    | Integrar ciclo de vida e erros   | Transições de estados e erros mapeados em pelo menos um fluxo end-to-end |
| 4    | Refino de DX e exemplos          | Exemplos de uso prontos + README consistente com Concept                 |

#### Exemplo de Fases (UI-first / Vertical slice)

| Fase | Objetivo                                   | Critério de “pronto”                                                                                 |
| ---- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| 1    | Casca de UI + mocks mínimos                | Pelo menos um fluxo visual mínimo funciona com dados mockados claramente marcados como provisórios  |
| 2    | Conectar UI a um core/backend parcial      | A mesma tela ou fluxo agora conversa com um pedaço real do core, cobrindo o caminho feliz básico    |
| 3    | Completar ciclo de vida e erros end-to-end | Erros e estados alternativos desse fluxo estão cobertos (UI + core) em pelo menos um cenário real   |
| 4    | DX/README/CI                               | README, exemplos e automações mínimas permitem reproduzir o fluxo principal em outro ambiente       |

Fase é **macro**: se não mudar o “estado do projeto”, não é fase, é tarefa.

---

### 5. Tarefas por fase (macro)

Tabela de tarefas que uma IA ou dev transforma direto em issues ou passos de alto nível.

Em modo `Core-first`, é comum que as primeiras tarefas foquem em componentes de core (por exemplo, um “kernel” de regras de negócio). Em modo `UI-first/Vertical slice`, é comum que as primeiras tarefas foquem em componentes de UI (por exemplo, uma tela principal), muitas vezes com casca + mocks antes de ligar no core real.

| ID  | Fase | Tipo    | Tarefa                                          | Origem              | Saída                                       | Pode ser paralelo? |
| --- | ---- | ------- | ----------------------------------------------- | ------------------- | ------------------------------------------- | ------------------ |
| T1  | 1    | ZenSpec | Criar ZenSpec de `ExemploKernel`                | Eng / Componentes   | `./specs/exemplo-kernel.zenspec.md`         | Não                |
| T2  | 1    | Código  | Implementar `ExemploKernel` a partir da ZenSpec | T1                  | `./src/kernel/exemplo-kernel/*`             | Não                |
| T3  | 1    | Teste   | Escrever testes de `ExemploKernel`              | T1                  | `./tests/unit/kernel/exemplo-kernel.test.*` | Sim                |
| T4  | 1    | ZenSpec | Criar ZenSpec de `ExemploClient`                | Eng / Componentes   | `./specs/exemplo-client.zenspec.md`         | Sim                |
| T5  | 1    | Código  | Implementar `ExemploClient`                     | T4, T2              | `./src/client/*`                            | Não                |
| T6  | 1    | Teste   | Escrever testes de `ExemploClient`              | T4                  | `./tests/unit/client.test.*`                | Sim                |
| T7  | 2    | ZenSpec | Criar ZenSpec de `ExemploOrchestrator`          | Eng / Ciclo de vida | `./specs/exemplo-orchestrator.zenspec.md`   | Não                |
| T8  | 2    | Código  | Implementar `ExemploOrchestrator`               | T7, T2, T5          | `./src/index.*`                             | Não                |
| T9  | 2    | Teste   | Escrever testes de `ExemploOrchestrator`        | T7                  | `./tests/unit/orchestrator.test.*`          | Sim                |

Regras:

- **Tipo**: ZenSpec, Código, Teste, Infra, Doc, etc.
- **Origem**: sempre algum Zen (Concept/Eng/Stack) ou outra tarefa (ex.: `T1`).
- **Saída**: caminho de arquivo ou pasta, em `código`.
- **Pode ser paralelo?**: “Sim/Não” para IA/Issues saber o que pode rodar junto.
- **Trio obrigatório: ZenSpec → Código → Teste.** Todo componente da tabela de componentes-alvo deve ter pelo menos 3 tarefas na tabela: uma de ZenSpec, uma de Código (derivada da ZenSpec) e uma de Teste. Isso vale tanto para componentes de core quanto de UI. Não pular a ZenSpec.
- **Nomes descritivos em português para ZenSpecs.** Na coluna Saída, o arquivo `.zenspec.md` deve usar nome que complete a frase "Este programa existe para ___" (verbo no infinitivo, em português). Exemplo: `montar-contexto-do-cliente.zenspec.md` em vez de `context-resolver.zenspec.md`. Dentro do arquivo, o título inclui o nome técnico entre parênteses: `# Montar contexto do cliente (retomarContextResolver)`.
- **Criar ou atualizar spec?** Tarefas de tipo ZenSpec devem seguir o critério da seção "Organização de specs" do ZenSpec.md: se o programa já tem ZenSpec filha, a tarefa é atualizar; se não tem, é criar. Se a mudança for regra de negócio do domínio (não contrato de programa), a tarefa atualiza a spec de módulo, não uma ZenSpec filha.

Componentes de UI seguem o mesmo trio. A ZenSpec de um componente de UI deve incluir layout, estados visuais e interações além do contrato técnico.

---

### 6. ZenTarefas (micro)

Lista mínima para uso diário: uma mistura de **pipelines** e **to‑dos**.

#### 6.1. Pipeline visual

Um pipeline geral para qualquer projeto:

```
Concept → Eng → Stack → Sensei → ZenSpec → Código → Testes → Exemplo → README
```

No dia a dia, marcar onde você está nesse fluxo.

#### 6.2. Blocos de trabalho

| Bloco | Quando usar | To‑dos mínimos |
| ----- | ----------- | -------------- |
| Kernel | Antes de qualquer feature | 1) ZenSpec kernel, 2) código kernel, 3) testes kernel |
| Client | Quando já existe kernel | 1) ZenSpec client, 2) código client, 3) testes client |
| Orquestração | Quando kernel + client existem | 1) ZenSpec orquestrador, 2) código, 3) testes ciclo de vida |
| DX | Quando o sistema já “anda” | 1) Exemplo simples, 2) README, 3) scripts de CI |

#### 6.3. Template de `*-tarefas.md`

Arquivo com **4 blocos de foco** para o dia a dia. Opcionalmente, **no topo** (antes de "Último movimento"), um bloco curto **Legenda do slice** (5–7 linhas ou um diagrama em texto): o filme em uma frase — quem entra, o que sai, o que fica oculto.

**Formato de cada tarefa (obrigatório):**

- **Linha 1 — humana + ID:** o que uma pessoa ganha ao terminar, em uma frase curta; mantém o ID macro (`RT3`, `PT1`…) e tags (`#faseN`, `#bloqueado(…)`).
- **Linha 2 — técnica:** prefixo `↳` + ação concreta (ZenSpec / código / teste), nome do programa entre crases (ex.: `retomarContextResolver`), caminho ou critério objetivo.

Exemplo:

```markdown
- [ ] T7 — Mesa de aprovação na tela (lista + editar + aprovar em lote)  #fase2
  ↳ ZenSpec de `retomarApprovalPanel` — `./Specs/retomar/aprovar-envio-em-lote.zenspec.md`
```

Template completo:

```markdown
# <Nome> — ZenTarefas

## Legenda do slice (opcional)
<!-- 5–7 linhas: história do fluxo em linguagem humana; diagrama em texto se ajudar. -->

## Último movimento
<!-- 1-3 linhas: "a última coisa que mexemos foi..." (contexto rápido para quem chega) -->


## Agora (Top 10)
<!-- Até 10 tarefas acionáveis. Use [>] para no máximo 1-2 itens simultâneos (WIP limit). -->
- [ ] ID — Entrega em linguagem humana (apelido opcional)  #faseN
  ↳ Detalhe técnico: ZenSpec / código / teste + `programa` + saída ou critério
- [>] ID — …  #faseN
  ↳ …
- [x] ID — …  #faseN
  ↳ …

## Pausado
<!-- Itens parados: mesmo formato duas linhas; motivo pode ir na linha humana ou após #bloqueado -->
- [ ] ID — …  #bloqueado(motivo)
  ↳ …

## Próximo
<!-- 3-5 itens candidatos; mesmo formato duas linhas -->
- [ ] ID — …
  ↳ …
```

Use `[>]` para no máximo 1-2 itens simultâneos (WIP limit). Cada **item** traz o ID macro (ex.: `PT3`) e tags opcionais (`#faseN`, `#bloqueado(motivo)`, `#mudou(decisão)`). **Issues no GitHub:** título sugerido `T<ID> — <primeira linha humana resumida>`; na descrição, colar a linha `↳` técnica.

---

### 7. Ganchos para GitHub

Mapa pronto para virar issues / milestones / PRs.

| Alvo       | Como usar                                                                             |
| ---------- | ------------------------------------------------------------------------------------- |
| Issues     | Cada linha de tarefa (ID) pode virar uma issue com título: `T<ID> - <Tarefa>`         |
| Labels     | Usar `tipo/<Tipo>` (ex.: `tipo/ZenSpec`, `tipo/Código`, `tipo/Teste`) e `fase/<Fase>` |
| Milestones | Cada Fase vira um milestone (`Fase 1 - Base`, `Fase 2 - Orquestração`)                |
| PRs        | Ideal: 1 PR por Fase ou subconjunto lógico de tarefas relacionadas                    |

Se não usar GitHub → escrever como o plano pode ser mapeado para a ferramenta equivalente (Jira, Linear, etc.).

---

### 8. Regras de passagem de fase

Checklist simples para saber se pode ir da Fase N para Fase N+1.

| Fase | Pode encerrar quando…                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------- |
| 1    | Todos os componentes base (de core e/ou de UI) têm ZenSpec aprovada, testes verdes e nenhum TODO pendente na implementação |
| 2    | Pontos de entrada (API, CLI ou UI) expõem tudo que a Eng Spec promete, com testes básicos verdes e exemplos mínimos       |
| 3    | Ciclo de vida e erros cobertos em pelo menos um fluxo end-to-end                                                           |
| 4    | README e exemplos permitem que alguém de fora use o sistema sem ler as ZenSpecs internas                                   |

Para projetos com forte camada de UI, considerar como critério adicional de Fase 1 ter pelo menos um fluxo visual mínimo (casca de UI + mocks) funcionando de ponta a ponta de forma navegável.

---

### 9. Escopo fora

O que **este** Sensei *não* faz:

- Gestão de equipe (quem faz o quê, datas, sprints).
- Prioridade de negócio (qual fase vem antes no roadmap da empresa).
- Estimativa de esforço (horas, story points).
- Decisões de stack (já estão no Stack Spec).
- Redefinir conceito ou arquitetura (isso é papel de Concept/Eng Spec).

---

### 10. Registro de mudanças

Mini changelog do plano. Toda revisão que mude fases, componentes ou critérios de pronto ganha uma linha aqui.

| ID | Origem (tarefa/evento) | O que mudou | Tarefas afetadas |
| -- | ---------------------- | ----------- | ---------------- |
|    |                        |             |                  |

Regra: só registrar mudanças que alterem o plano macro (fases, componentes, critérios). Ajustes pequenos em `./<nome>-tarefas.md` não precisam de entrada aqui.

---

## Antes de escrever

- Os componentes principais já estão descritos na Eng Spec?
- A stack mínima já está definida no Stack Spec?
- O conceito está claro o suficiente para dizer a ordem de valor (o que é mais essencial)?
- Você sabe **qual é o estado “mínimo usável”** do projeto?

Se não sabe → voltar para Concept/Eng/Stack antes de escrever o Sensei.

---

## Depois de escrever

- Toda tarefa tem **Origem** e **Saída** clara?
- Toda dependência importante aparece na coluna **Depende de** ou **Origem**?
- Dá para alguém (ou uma IA) começar na primeira tarefa e seguir sem perguntar “e agora?”?
- Em 10 segundos olhando as tabelas você sabe:
  - Em que Fase o projeto está
  - Qual é a próxima tarefa
- Dá para transformar a tabela de Tarefas diretamente em issues no GitHub?
- O Sensei tem seção de “Registro de mudanças” (mesmo que vazia)?

Se alguma resposta for “não” → o Sensei ainda não está pronto.
