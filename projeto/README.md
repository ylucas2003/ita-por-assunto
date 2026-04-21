# Banco ITA · IME — por assunto

Banco de questões dos vestibulares do ITA e do IME, organizado por tópico do
edital. Dividido em duas partes independentes:

- **[site/](site/)** — interface web estática, pronta para hospedar.
- **[pipeline/](pipeline/)** — scripts Python que processam PDFs de provas em
  JSONs canônicos e geram os HTMLs.

---

## 1. Interface (o que é publicado)

[site/](site/) contém dois arquivos:

| Arquivo | Descrição |
|---|---|
| [site/index.html](site/index.html) | Tela de login (cosmética — redireciona para o banco). |
| [site/banco_unificado.html](site/banco_unificado.html) | Banco completo: Física, Química e Matemática, ITA + IME, com filtros por ano, fase, tópico e estatísticas de recorrência. |

O HTML do banco embute todos os dados das questões inline (~1,8 MB). As
imagens das questões são servidas do bucket público
`s3://ita-por-assunto/imagens/`, então **o site roda em qualquer host
estático** sem backend.

### Hospedar (3 opções)

**GitHub Pages — recomendado.** Já existe um workflow em
[.github/workflows/deploy.yml](.github/workflows/deploy.yml) que publica
`site/` automaticamente a cada push na `main`. Para ativar:

1. No repositório, vá em **Settings → Pages → Source: GitHub Actions**.
2. Faça push na `main`. O site fica em `https://<user>.github.io/<repo>/`.

**Cloudflare Pages / Netlify / Vercel.** Conecte o repo, configure:
- Build command: _(nenhum)_
- Output / publish directory: `site`

**S3 + CloudFront (mesmo bucket das imagens).**
```bash
aws s3 sync site/ s3://ita-por-assunto/ --exclude ".*" --acl public-read
```
Ative "Static website hosting" no bucket e defina `index.html` como
documento índice.

### Republicando após mudanças

Depois de rodar a pipeline (ver abaixo), sincronize a saída com `site/`:

```bash
cp output/banco_unificado.html site/banco_unificado.html
git add site/banco_unificado.html
git commit -m "atualiza banco"
git push   # GitHub Pages publica sozinho
```

---

## 2. Pipeline (como os dados são gerados)

### Filosofia

1. **JSON como fonte da verdade.** Cada questão é um JSON independente em
   [questoes_json/](questoes_json/). HTML, LaTeX, DOCX e PDF são gerados a
   partir dele — dá para mudar o template e regerar tudo sem reprocessar PDFs.
2. **Imagem em vez de extração de texto.** Cada questão é recortada como PNG
   (enunciado + alternativas + figura). Isso evita problemas com fórmulas e
   preserva o visual original da prova.
3. **Texto como metadado.** Extraímos o texto para permitir busca e
   classificação automática pelo Claude.
4. **Etapas independentes.** Cada script faz uma coisa só; dá pra rerodar
   qualquer etapa sem refazer as outras.

### Estrutura do repo

```
.
├── site/                     # (publicado) interface estática
├── config/                   # taxonomias dos editais e schema JSON
│   ├── schema_questao.json
│   ├── taxonomia.json              # Física
│   ├── taxonomia_matematica.json
│   └── taxonomia_quimica.json
├── questoes_json/            # JSONs canônicos (uma pasta por prova) — fonte da verdade
├── pipeline/                 # scripts Python
│   ├── extrair_prova.py          # 1. texto + render de páginas
│   ├── recortar_questoes.py      # 2. recorta cada questão em PNG
│   ├── extrair_gabarito.py       # 3. lê o gabarito
│   ├── classificar.py            # 4. classificação por tópico (assistida)
│   ├── renderizar_html.py        # 5. gera o HTML
│   ├── gerar_banco_unificado.py  # gera o banco consolidado
│   ├── pipeline_completo.py      # orquestra 1–3 numa chamada
│   ├── processar_tudo.py         # roda todos os anos/matérias
│   ├── processar_ime.py          # equivalente p/ IME 1ª fase
│   ├── processar_2fase.py        # ITA 2ª fase
│   ├── processar_ime_2fase.py    # IME 2ª fase
│   ├── reclassificar.py          # re-executa classificação
│   └── upload_s3.py              # sobe imagens p/ o bucket
│
├── pdfs_originais/           # [gitignored] coloque aqui os PDFs
│   ├── ita_fase1/ ita_fase2/
│   └── ime_fase1/ ime_fase2/
├── paginas_renderizadas/     # [gitignored] gerado
├── imagens/                  # [gitignored] gerado (e espelhado no S3)
├── output/                   # [gitignored] HTMLs intermediários
└── logs/                     # [gitignored]
```

### Setup

```bash
pip install pymupdf pytesseract pillow jinja2 boto3
# Ubuntu/Debian (OCR para páginas escaneadas):
sudo apt-get install tesseract-ocr tesseract-ocr-por

# Credenciais AWS (só se for subir imagens novas ao S3):
cp .env.example .env  # edite com suas chaves
```

### Processando uma prova nova

```bash
# 1. Coloque os PDFs em pdfs_originais/ita_fase1/ (ou a pasta apropriada)

# 2. Extração + recorte + gabarito, tudo de uma vez:
python pipeline/pipeline_completo.py pdfs_originais/ita_fase1/2019_fase1.pdf \
    --ano 2019 --fase 1 --materia Física \
    --gabarito pdfs_originais/ita_fase1/gabarito_2019.pdf

# 3. Classificação (usando Claude Code) — ver seção abaixo.

# 4. Regerar o banco unificado:
python pipeline/gerar_banco_unificado.py

# 5. Publicar:
cp output/banco_unificado.html site/
```

Ou rode tudo de uma vez:
```bash
python pipeline/processar_tudo.py
```

### Classificação com Claude Code

A classificação exige raciocínio — é feita com Claude.

```bash
python pipeline/classificar.py listar ita_2019_fase1 > pendentes.txt
```

Abra `pendentes.txt` no VSCode com Claude Code e peça:

> Para cada questão listada abaixo, classifique-a segundo a taxonomia do
> edital (em `config/`). Gere um `_classificacao_patch.json` no formato:
> `{ "qNN": { "topicos_ids": [...], "confianca": "alta|media|baixa",
> "observacao": "..." } }`. As imagens estão em `imagens/ita_2019_fase1/`.

Aplique o patch:
```bash
python pipeline/classificar.py aplicar ita_2019_fase1 _classificacao_patch.json
```

### Simulados filtrados

```bash
# Por bloco:
python pipeline/renderizar_html.py \
    --provas ita_2018_fase1 ita_2019_fase1 ita_2020_fase1 \
    --bloco "Eletromagnetismo" \
    --titulo "Simulado Eletromagnetismo 2018-2020" \
    --saida simulado_eletro.html

# Por tópico específico:
python pipeline/renderizar_html.py \
    --provas ita_2018_fase1 ita_2019_fase1 \
    --topico 7.1 \
    --titulo "Óptica Geométrica"
```

---

## 3. Limitações conhecidas

- Provas 100% escaneadas com qualidade ruim podem falhar o OCR em localizar
  "Questão N". O script avisa; nesses casos é preciso registrar coordenadas
  manuais (ainda não implementado).
- A última questão de cada matéria pode trazer um pequeno rodapé (número de
  página) no recorte — visível mas não atrapalha o uso.
- A classificação via Claude precisa de revisão humana — questões mistas têm
  ambiguidade legítima entre tópicos.

## 4. Extensões naturais

- **Outros vestibulares.** O pipeline não assume ITA/IME em lugar nenhum; é
  só passar `--vestibular X` na extração.
- **Outros formatos (LaTeX / DOCX).** Como cada questão é uma imagem, basta
  trocar o template Jinja2: `\includegraphics{imagens/.../qNN.png}` para
  LaTeX, `doc.add_picture(...)` para DOCX via `python-docx`.
- **Busca textual avançada.** Os JSONs independentes podem ser carregados em
  SQLite ou Elasticsearch sem esforço.
