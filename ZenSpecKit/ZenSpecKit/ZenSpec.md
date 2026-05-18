# Zen Spec Kit

Especificações claras, sem ambiguidade. Spec diz **o quê**; plano e código dizem **como**.

---

## Objetivo

Produzir specs:

- **Determinísticas** — Se X → Y. Sem “talvez”, “melhor”, “adequado”.

- **Auditáveis** — Rastreável de regra a comportamento.

- **Testáveis** — Critérios objetivos.

- **Compatíveis com IA e com equipes** — Formato que qualquer um (ou qualquer modelo) consiga seguir.

---

## Fonte da Verdade

Esta spec é a única fonte válida de comportamento do sistema.

Código, testes e validações devem ser derivados exclusivamente dela.

Se houver divergência entre código e spec, a spec prevalece.

Nada fora desta spec define comportamento.

Alterações no sistema exigem alteração prévia na spec.

---

## Princípios

- **O que está na spec é o sistema. O que não está, não existe.** Comportamento não especificado não é lacuna — é ausência de requisito. Especifique ou não acontece.

- **Duas linhas por explicação.** Se precisar de mais, a regra ou o conceito ainda não está claro o suficiente.

- **Spec ≠ Plano ≠ Código.** Não misturar requisito com arquitetura ou implementação.

- Cada programa do pipeline deve poder ser implementado isoladamente apenas com sua seção. Nenhuma dependência implícita fora do contrato.

- **Ontologia de atores:** Todo sujeito ativo no texto (“X lê”, “X decide”, “X chama”, “X orquestra”) deve ser exatamente um destes:
  
  - um programa do pipeline com seção de Lógica e Contrato,
  
  - uma Interface declarada,
  
  - um sistema externo listado como dependência.  
    Se não se encaixar nessas categorias, esse ator não existe na spec.

- **Programa simples vs. orquestrador:**
  
  - Programa simples: transforma entradas em saídas sem chamar outros programas do pipeline.
  
  - Orquestrador: compõe outros programas, decide ordem, repetição ou tratamento de erro.  
    Ambos são programas de primeira classe: têm nome em `código`, seção de Lógica e Contrato e aparecem no fluxo. Não existe orquestrador implícito.

- **Um comportamento = uma regra ou um estado.** Nada de "o sistema às vezes faz X" sem estar na spec.

- **Um programa, uma razão para mudar.** Cada programa do pipeline muda por um único motivo de negócio — não por dois atores diferentes.

- **Só o necessário.** Não especificar o que não for necessário para contrato, teste ou decisão.

- **Legível sozinha.** A spec deve ser compreensível por quem não participou das discussões orais do projeto.

- **Proibições:** Não inventar regras. Não aceitar ambiguidade. Não deixar comportamento silencioso.

- **Dados antes de dependências.** Nos contratos, parâmetros de dados vêm primeiro; dependências externas (bridge, banco, índices) aparecem depois e agrupadas em um único parâmetro.

- **Panorama completo.** Na tabela do pipeline, marcar opcional em Recebe (`campo?` ou "(opcional)"); precondição em uma linha quando o programa depender de estado anterior. O contrato é a fonte da verdade; o panorama não omite o que o contrato explicita.

- **Edge cases.** Lista "Se X → Y", uma linha por caso, após as regras do programa; não duplicar o que já está nas regras.

- **Escopo fora.** Uma seção ou lista curta com o que a spec não cobre.

- **Config, tipo, dependência.** Uma linha quando existir: config fixa do programa; tipo complexo → referenciar fonte (arquivo/schema); dependência abstraída → operações em uma linha (implementação de referência opcional).

- **Critérios de aceitação.** Regras + edge cases = critérios; se insuficiente, uma frase por programa.

- **Falha explícita.** Em I/O ou chamada externa: falhar explícito, sem sucesso parcial silencioso.

- **Idempotência e efeito.** Quando relevante: uma linha (ex. reexecutar = mesmo resultado; só leitura; não persiste).

---

## Organização de specs

### Dois níveis

| Nível | Arquivo | Escopo | Quando criar |
| ----- | ------- | ------ | ------------ |
| **Spec de módulo** | `spec.md` (uma por pasta de domínio) | Conceito do domínio, regras de negócio, Interface completa | Quando o módulo/domínio nasce |
| **ZenSpec de componente** | `nome-descritivo.zenspec.md` (uma por programa) | Pipeline, Contrato, Regras, Edge cases, Critérios de aceitação | Quando o Sensei gera uma tarefa de tipo "ZenSpec" |

A spec de módulo é a "mãe". As ZenSpecs de componente são "filhas" que vivem na mesma pasta.

```
Specs/retomar/
  spec.md                                ← módulo (guarda-chuva)
  montar-contexto-do-cliente.zenspec.md  ← componente (filha)
  gerar-mensagem-baseline.zenspec.md     ← componente (filha)
```

### Criar ou atualizar?

| A mudança é sobre… | Ação |
| ------------------- | ---- |
| Regra de negócio, conceito ou interface do domínio | **Atualizar** a spec de módulo |
| Contrato, pipeline ou edge cases de um programa específico | **Criar ou atualizar** a ZenSpec filha |
| Programa que ainda não tem ZenSpec filha | **Criar** ZenSpec filha |
| Programa que já tem ZenSpec filha | **Atualizar** a ZenSpec filha existente |

A spec de módulo não detalha contratos de componentes individuais. Quando uma ZenSpec filha é criada, o contrato daquele programa passa a viver **só** na filha; a spec de módulo mantém apenas a referência e o contexto de negócio.

### Nomes de arquivo

O nome do arquivo `.zenspec.md` deve completar a frase **"Este programa existe para ___"**, em português, usando verbos no infinitivo.

Exemplos:

| Nome técnico (no código) | Nome do arquivo |
| ------------------------ | --------------- |
| `retomarContextResolver` | `montar-contexto-do-cliente.zenspec.md` |
| `retomarBaselineAgent` | `gerar-mensagem-baseline.zenspec.md` |
| `retomarSendRecorder` | `gravar-envio-no-historico.zenspec.md` |
| `retomarApprovalPanel` | `aprovar-envio-em-lote.zenspec.md` |
| `retomarExperimentOrchestrator` | `comparar-rag-vs-baseline.zenspec.md` |

Dentro do arquivo, o título pode incluir o nome técnico entre parênteses para manter o vínculo com o código:

```markdown
# Montar contexto do cliente (`retomarContextResolver`)
```

Specs de módulo mantêm o nome `spec.md` (sem prefixo descritivo) porque representam o domínio inteiro.

---

## Formato Zen

### Estrutura por feature:

Toda feature com seção de Lógica DEVE seguir esta ordem:

1. **Conceito** — O que é, em 2-3 frases. Linguagem humana, sem contrato. Quem lê o Conceito entende o domínio sem ler o resto.
2. **Lógica** — Regras, contratos, pipeline, edge cases, critérios de aceitação. Tudo determinístico. Quem lê a Lógica consegue implementar sem ler a Interface.
3. **Interface** (se houver UI) — Layout, estados visuais, hierarquia, interações. Quem lê a Interface consegue desenhar a tela sem ler a Lógica inteira.

Conceito responde "o que é". Lógica responde "como funciona". Interface responde "como aparece".

Sem numeração fixa, mas a ordem é sempre esta. Features sem UI omitem a seção Interface. Subseções dentro de cada bloco são livres (`[Nome da feature]` com subseções).

### Intenção por feature:

Antes de qualquer seção de feature, uma linha:

Esta feature existe para que [quem] consiga [fazer o quê] sem precisar de [o quê].

### Pipeline & fluxos:

**1. Linha do fluxo (visão geral):**

```
origem  →  etapa1  →  etapa2  →  destino
```

**2. Tabela imediata abaixo:**

| Programa | Recebe  | Faz       | Manda para   |
| -------- | ------- | --------- | ------------ |
| `nome`   | entrada | o que faz | próximo ou — |

Na coluna Recebe: marcar opcional com `?` ou "(opcional)" quando fizer diferença. Se o programa depender de estado anterior (ex. banco aberto), uma linha de precondição na seção do programa ou abaixo da tabela. Panorama não deixa furo; contrato abaixo é a fonte da verdade.

**3. Ao detalhar a Lógica de um programa**, repetir a linha do fluxo só para ele:

```
anterior  →  este_programa  →  próximo
```

Assim não se perde onde o programa está no pipe

### Contratos

Sempre que houver contrato (serviço, motor, API): entradas e saídas explícitas.

Para cada programa do pipeline, a seção deve conter obrigatoriamente:

#### Contrato

Entrada:

- campo: tipo

- campo: tipo

Saída:

- campo: tipo

- campo: tipo

Erros:

- código → condição

Nenhum comportamento pode existir fora do contrato declarado.

- **Assinatura única.** A ordem e o nome dos parâmetros definidos na spec devem ser iguais à assinatura das funções no código e nos testes.

### Edge cases

Lista "Se X → Y" (uma linha por caso), logo após as Regras do programa. Só o que for exceção ou limite; não repetir o que já está nas regras. Ex.: `MessageDB vazio → [].` / `Erro ao acessar → falha explícita.`

### Nomes de programas

Programas do pipeline aparecem sempre em `código` — em tabelas, fluxos e texto. Consistente, sem variação.

### Histórico de decisão

Regras que já foram contestadas ou substituídas carregam uma linha:

Esta regra substitui `X` porque `Y`.

**Um programa, uma responsabilidade :** Cada programa do pipeline faz uma coisa; nomes e contratos permitem composição — trocar um programa não exige reescrever o resto da spec.

---

#### Antes de gerar (Clarificação)

Identificar antes de escrever:

- Termos vagos ou com dois sentidos possíveis.

- Comportamentos esperados não descritos.

- Dependências externas não especificadas.

- Atores implícitos

Se o comportamento não pode ser determinado → perguntar. Se pode ser especificado agora → especificar.

---

## Depois de gerar (Integridade)

- Toda regra está na forma "Se X → Y"?

- Nenhuma regra implícita fora do texto?

- Nenhum comportamento silencioso (sem regra correspondente)?

- Nenhum conflito entre regras ou seções?

- Toda entrada tem saída rastreável?

- Nenhuma mistura de spec com implementação?

- Todo sujeito ativo no texto existe como programa, Interface ou sistema externo declarado?

- Existe algum ator citado que não possui seção própria ou não aparece no fluxo?

- Para cada fluxo `origem → ... → destino`, está claro quem recebe o gatilho externo e quem devolve o resultado final?

- Todo programa com seção de Lógica tem seção de Contrato e linha de fluxo `anterior → este → próximo`?

- Todo programa aparece como `código` em tabelas, fluxos e texto?

- A spec é compreensível sem conhecimento oral do projeto?

- O escopo fora da spec está explicitado?

- Para cada programa, edge cases (lista Se X → Y) e critérios de aceitação estão explícitos onde necessário?

- Qualquer pessoa que não participou das discussões consegue derivar um caso de teste para cada regra sem fazer perguntas.

- Para cada programa do pipeline, existe teste chamando a função com a mesma assinatura (parâmetros e ordem) descrita na spec?
