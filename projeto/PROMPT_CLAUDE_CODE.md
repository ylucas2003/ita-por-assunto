# Prompt para o Claude Code — Processar lote de provas ITA

Cole este prompt no Claude Code com o projeto `projeto_ita/` aberto.
O agente fará o processamento completo de todas as provas+gabaritos
que encontrar em `pdfs_originais/`, acumulando tudo num HTML único.

---

## PROMPT

Você tem acesso ao projeto `projeto_ita/` e à pasta `pdfs_originais/` contendo
PDFs de provas e gabaritos do ITA. Seu objetivo é **processar todas as provas
ainda não processadas**, classificar as questões por tópico, e gerar um HTML
acumulado com todas elas.

### Contexto que você precisa ler antes de começar

1. Leia `README.md` — entenda a filosofia (JSON canônico + imagem + texto).
2. Leia `config/taxonomia.json` — é a sua referência de classificação.
3. Liste `questoes_json/` para ver quais provas já foram processadas; não
   refaça essas (são idempotentes, mas reprocessar desperdiça tempo).

### Regras do jogo

- **Não edite os scripts do pipeline.** Se algum falhar numa prova específica,
  pule a prova, registre o erro em `logs/processamento.log`, e continue com
  as outras. Não tente "consertar" modificando os scripts — isso é trabalho
  que o humano vai fazer depois de ver o log.
- **Trabalhe prova por prova.** Não tente paralelizar nem juntar etapas.
  A ordem é: pareamento → pipeline_completo → classificação → próxima prova.
- **Classificação é tarefa sua.** Para cada prova, depois de rodar o pipeline
  automático, abra as imagens das questões (`imagens/{prova_id}/`) e os
  JSONs (`questoes_json/{prova_id}/`), e gere o arquivo
  `questoes_json/{prova_id}/_classificacao_patch.json` com a classificação
  de todas as 12 questões de Física.
- **Seja conservador na classificação.** Questões mistas são comuns no ITA —
  use 2-3 tópicos quando apropriado, mas não espalhe em 5. Preencha o campo
  `observacao` com uma frase explicando a escolha.
- **Ao final, gere UM HTML acumulado** com todas as provas processadas, e
  imprima um resumo.

### Passos

**1. Descoberta e pareamento de PDFs.**

Liste os arquivos em `pdfs_originais/`. Você vai encontrar dois tipos de PDFs:
provas e gabaritos. Os nomes podem variar (`2018_fase1.pdf`, `ita-2018.pdf`,
`gabarito_2018.pdf`, `gab2018.pdf`, etc.).

Pareie-os por ano usando esta heurística:
- Extraia o ano de 4 dígitos (20XX) do nome do arquivo.
- Classifique como gabarito se o nome contém "gab" (case-insensitive).
- Caso contrário, é prova.
- Ignore PDFs sem ano reconhecível (peça confirmação ao humano no final).

Crie um dict em memória: `{ano: {"prova": Path, "gabarito": Path | None}}`.

**2. Para cada par (ano, prova, gabarito) não processado:**

Verifique se `questoes_json/ita_{ano}_fase1/_relatorio.json` já existe. Se
existir, pule essa prova.

Caso contrário, execute:

```bash
python pipeline/pipeline_completo.py pdfs_originais/{nome_prova} \
    --ano {ano} --fase 1 --materia Física \
    --gabarito pdfs_originais/{nome_gabarito}
```

Se o gabarito for `None`, omita `--gabarito`. Se o comando sair com código
diferente de 0, registre em `logs/processamento.log` e vá para a próxima.

**3. Classificação.**

Depois que o pipeline automático terminou com sucesso para uma prova:

a. **Leia os 12 JSONs** em `questoes_json/ita_{ano}_fase1/q01.json` até
   `q12.json`. O campo `enunciado_md` geralmente tem o texto da questão
   com qualidade suficiente para classificar. As alternativas também.

b. **Só abra a imagem da questão** (`imagens/ita_{ano}_fase1/{id}_qNN.png`)
   se o `enunciado_md` estiver vazio, truncado, ou cheio de lixo de OCR
   (sinal de que a página era escaneada e o OCR falhou). Ler imagem é
   custoso; use quando o texto não bastar.

c. Para cada questão, decida quais `topicos_ids` da taxonomia se aplicam.
   Use a taxonomia em `config/taxonomia.json` — os IDs válidos são os
   da forma "X.Y" (ex: "2.3" = Dinâmica, "8.4" = Indução EM).

d. Gere `questoes_json/ita_{ano}_fase1/_classificacao_patch.json`. Exemplo
   real (prova 2019) do formato esperado:

```json
{
  "_comentario": "Classificado por Claude Code",
  "q01": {
    "topicos_ids": ["7.2", "7.1", "6.1"],
    "confianca": "alta",
    "observacao": "Mista: onda EM transversal (7.2), reflexão total (7.1), brisa marítima pelo calor específico (6.1).",
    "classificado_por": "claude"
  },
  "q02": {
    "topicos_ids": ["2.3"],
    "confianca": "alta",
    "observacao": "Dinâmica do movimento circular com força centrípeta envolvendo mola.",
    "classificado_por": "claude"
  }
}
```

Regra prática para número de `topicos_ids`:
- **1 tópico:** questão puramente de um assunto (ex: só lentes delgadas).
- **2 tópicos:** combinação natural (ex: gravitação + MHS quando é túnel
  pelo centro da Terra; fotoelétrico + circuito elétrico).
- **3 tópicos:** só em questões com afirmações I/II/III que tocam em
  assuntos genuinamente diferentes.
- **Nunca 4+.** Se precisa de 4 tópicos, você está "jogando seguro" —
  escolha os 2-3 mais essenciais.

e. Aplique o patch:

```bash
python pipeline/classificar.py aplicar ita_{ano}_fase1 \
    questoes_json/ita_{ano}_fase1/_classificacao_patch.json
```

f. **Se o JSON de alguma questão tem `enunciado_md` vazio/truncado E você
   também não consegue classificar pela imagem** (OCR falhou completamente
   e a imagem tem problema): marque na classificação com
   `"topicos_ids": [], "confianca": "baixa", "observacao": "Texto não
   extraível — precisa revisão humana"`. O patch aceita isso; o renderizador
   coloca essas questões numa seção "Não classificadas" no fim.

**4. Geração do HTML acumulado.**

Depois de processar todas as provas, liste as provas que têm classificação
completa (todos os JSONs com `status.classificado == true`) e rode:

```bash
python pipeline/renderizar_html.py \
    --provas {lista_de_prova_ids_separados_por_espaço} \
    --titulo "Banco de Questões ITA — Física" \
    --saida banco_completo.html
```

**5. Relatório final.**

Imprima um resumo para o humano contendo:
- Quantas provas foram processadas nesta execução
- Quantas foram puladas (já processadas antes)
- Quantas falharam (com links para os erros no log)
- Caminho do HTML final gerado
- Top 5 tópicos mais frequentes (do output do renderizar_html.py) como
  prévia da estatística acumulada

### Checklist de conclusão

Antes de encerrar, confirme:

- [ ] Todas as provas em `pdfs_originais/` foram tentadas (processadas ou logadas)
- [ ] Todos os JSONs de questões têm `gabarito` preenchido (quando havia PDF de gabarito)
- [ ] Todos os JSONs têm `status.classificado == true` (pelo menos das provas bem-sucedidas)
- [ ] `output/banco_completo.html` existe e abre sem erro no navegador
- [ ] `logs/processamento.log` foi criado se houve erros

### Se você encontrar algo inesperado

- Layout de prova muito diferente (pipeline falha): registre no log e pule.
- Gabarito em formato não-tabular (pipeline extrai menos que 12 letras): a
  classificação pode prosseguir, só o campo `gabarito` ficará null. Registre
  aviso no log.
- Uma prova que não tem 12 questões de Física (ITA mais antigo?): processe
  mesmo assim, o pipeline é tolerante a número variável.
- Dúvida de classificação séria entre 2 tópicos: use `confianca: "media"` e
  explique na observação. O humano vai revisar.
- PDF sem ano no nome: pergunte ao humano no final, não adivinhe.

Pode começar.
