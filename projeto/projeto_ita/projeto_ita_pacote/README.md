# Pipeline ITA — Organizador de Provas por Assunto

Sistema para processar provas antigas do ITA, recortar as questões como imagens,
classificá-las por tópico (seguindo o edital) e gerar simulados em HTML com
gabarito e estatísticas de recorrência.

## Filosofia do projeto

1. **JSON como fonte da verdade.** Cada questão é um JSON independente. HTML,
   LaTeX, DOCX e PDF são gerados a partir dele. Você pode mudar o template e
   regerar tudo sem reprocessar PDFs.
2. **Imagem em vez de extração de texto.** Cada questão é recortada como PNG
   (enunciado + alternativas + figura). Isso evita problemas com fórmulas,
   símbolos matemáticos e páginas escaneadas — e preserva o visual original da
   prova.
3. **Texto como metadado.** Mesmo usando imagem no render, extraímos o texto
   para permitir busca e classificação automática pelo Claude.
4. **Pipeline composto em etapas independentes.** Cada script faz uma coisa só;
   você pode rodar de novo qualquer etapa sem refazer as outras.

## Estrutura

```
projeto_ita/
├── pdfs_originais/           # coloque aqui os PDFs das provas e gabaritos
├── paginas_renderizadas/     # imagens das páginas (geradas automaticamente)
├── imagens/                  # recortes das questões (gerados automaticamente)
├── questoes_json/            # JSONs canônicos (uma pasta por prova)
├── config/
│   ├── taxonomia.json        # edital do ITA em árvore consultável
│   └── schema_questao.json   # documentação do formato JSON
├── pipeline/
│   ├── extrair_prova.py      # etapa 1: extrai texto e renderiza páginas
│   ├── recortar_questoes.py  # etapa 2: recorta cada questão como PNG
│   ├── extrair_gabarito.py   # etapa 3: lê o PDF do gabarito
│   ├── classificar.py        # etapa 4: classifica por tópico
│   └── renderizar_html.py    # etapa 5: gera o HTML final
└── output/                   # HTMLs gerados
```

## Dependências

```bash
pip install pymupdf pytesseract pillow jinja2
# No Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

O `tesseract-ocr-por` só é necessário se alguma das suas provas tiver páginas
escaneadas (sem texto selecionável). O ITA frequentemente mistura páginas
nativas e escaneadas no mesmo PDF.

## Fluxo de uso — processando uma nova prova

Suponha que você baixou `ita_2018_fase1.pdf` e `gabarito_2018.pdf`:

```bash
# 1. Coloque os PDFs na pasta
cp ita_2018_fase1.pdf pdfs_originais/

# 2. Extrair texto e renderizar páginas (demora ~10s por prova)
python pipeline/extrair_prova.py pdfs_originais/ita_2018_fase1.pdf \
    --ano 2018 --fase 1 --materia Física

# 3. Recortar cada questão como imagem
python pipeline/recortar_questoes.py ita_2018_fase1

# 4. Extrair e aplicar o gabarito
python pipeline/extrair_gabarito.py pdfs_originais/gabarito_2018.pdf ita_2018_fase1

# 5. Classificar (vide próxima seção)

# 6. Gerar HTML
python pipeline/renderizar_html.py --provas ita_2018_fase1 \
    --titulo "Simulado ITA 2018" --saida simulado_2018.html
```

## Classificação usando Claude Code

A etapa de classificação exige raciocínio, então ela é feita usando o Claude
(você pode abrir o VSCode com Claude Code e pedir para ele fazer).

Fluxo recomendado:

1. Rode o listar para ver as questões pendentes:
   ```bash
   python pipeline/classificar.py listar ita_2018_fase1 > pendentes.txt
   ```

2. Abra `pendentes.txt` no VSCode. Peça ao Claude:

   > Para cada questão listada abaixo, classifique-a segundo a taxonomia do
   > edital do ITA (também listada no arquivo). Gere um arquivo
   > `_classificacao_patch.json` com o formato:
   > `{ "qNN": { "topicos_ids": [...], "confianca": "alta|media|baixa",
   > "observacao": "..." } }`. Use múltiplos `topicos_ids` se a questão for
   > mista. As imagens das questões estão em `imagens/ita_2018_fase1/`.

3. Aplique o patch:
   ```bash
   python pipeline/classificar.py aplicar ita_2018_fase1 _classificacao_patch.json
   ```

## Gerando simulados filtrados

Além do simulado completo, você pode gerar recortes temáticos:

```bash
# Todas as questões de Eletromagnetismo (de várias provas)
python pipeline/renderizar_html.py \
    --provas ita_2018_fase1 ita_2019_fase1 ita_2020_fase1 \
    --bloco "Eletromagnetismo" \
    --titulo "Simulado Eletromagnetismo 2018-2020" \
    --saida simulado_eletro.html

# Só um tópico específico: Óptica Geométrica (7.1)
python pipeline/renderizar_html.py \
    --provas ita_2018_fase1 ita_2019_fase1 \
    --topico 7.1 \
    --titulo "Simulado Óptica Geométrica"
```

Quanto mais provas você tiver classificadas, mais úteis as estatísticas de
recorrência ficam (mostram o que o ITA cobra com mais frequência).

## Migrando para outros formatos

### Para LaTeX / PDF
Como cada questão é uma imagem, o caminho mais simples é:
- Escrever um template LaTeX novo (substituindo Jinja2 HTML por Jinja2 LaTeX)
  que faz `\includegraphics{imagens/.../qNN.png}` para cada questão.
- Compilar com `pdflatex`.

O JSON canônico tem tudo que o template precisa: número, tópicos, gabarito,
caminho da imagem.

### Para DOCX
Use `python-docx` e insira as imagens com `doc.add_picture(caminho, width=...)`.
O agrupamento por tópico segue a mesma lógica do renderizador HTML.

## Extensões naturais

- **Outras matérias.** O script já suporta `--materia Matemática`, `Química`,
  etc. A taxonomia em `config/taxonomia.json` é só da Física — se quiser
  processar outras matérias, adicione suas taxonomias em novos arquivos.
- **Outros vestibulares.** O pipeline não assume ITA em lugar nenhum; é só
  passar `--vestibular IME` na extração. A faixa de questões por matéria
  (hoje fixa no topo de `extrair_prova.py`) talvez precise de ajuste.
- **Banco de questões pesquisável.** Como os JSONs são independentes, você
  pode carregá-los em SQLite / Elasticsearch sem esforço para fazer busca
  textual avançada.

## Limitações conhecidas

- Para provas 100% escaneadas com qualidade ruim, o OCR pode falhar em
  localizar algumas "Questão N". Se isso acontecer, o script avisa e você
  pode registrar coordenadas manuais num arquivo `recortes_manuais.json`
  (ainda não implementado — ver TODO).
- A última questão de cada matéria pode trazer um pequeno rodapé (número da
  página) no recorte porque não há "Questão N+1" para delimitar. É visível
  mas não atrapalha o uso.
- A classificação via Claude é de responsabilidade sua revisar — questões
  mistas podem ter ambiguidade legítima entre tópicos.
