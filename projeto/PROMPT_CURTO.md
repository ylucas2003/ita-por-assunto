# Prompt curto — adicionar mais provas ao banco

Use este prompt quando você já tem o banco funcionando e só quer adicionar
provas novas. É uma versão enxuta do `PROMPT_CLAUDE_CODE.md`.

---

## PROMPT

Adicione ao banco as provas novas que estão em `pdfs_originais/` e ainda
não foram processadas (verifique em `questoes_json/`). Para cada uma:

1. Pareie a prova com seu gabarito pelo ano (nome com "gab" = gabarito).
2. Rode `python pipeline/pipeline_completo.py` com `--ano`, `--fase 1`,
   `--materia Física` e `--gabarito` apontando para o PDF do gabarito.
3. Classifique as 12 questões lendo as imagens em `imagens/ita_{ano}_fase1/`
   e a taxonomia em `config/taxonomia.json`. Gere
   `questoes_json/ita_{ano}_fase1/_classificacao_patch.json` e aplique
   com `python pipeline/classificar.py aplicar ...`.
4. Regere o HTML acumulado listando **todas** as provas já classificadas:
   `python pipeline/renderizar_html.py --provas {todas} --titulo "Banco ITA — Física" --saida banco_completo.html`

Pule provas já processadas (`questoes_json/ita_{ano}_fase1/_relatorio.json`
existe). Se alguma falhar, registre em `logs/processamento.log` e continue.
No fim, imprima quantas foram adicionadas e os top 5 tópicos mais frequentes
no banco completo.
