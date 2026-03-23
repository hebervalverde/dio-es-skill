---
name: dio-es
description: >
  Pesquisa e download de publicações do Diário Oficial do Estado do Espírito
  Santo (DIO-ES) via API pública. Sem autenticação — dados 100% abertos.
  Use esta skill SEMPRE que o usuário quiser pesquisar no DIO-ES, buscar
  publicações oficiais do Espírito Santo, procurar ordens de fornecimento,
  atas de registro de preços, licitações, contratos, portarias, decretos,
  editais, ou qualquer ato publicado no Diário Oficial do ES.
  Dispare quando o usuário mencionar: DIO, DIO-ES, diário oficial, diário
  oficial do ES, diário oficial do Espírito Santo, pesquisar no diário,
  buscar publicação oficial, baixar do DIO, pesquisar licitação ES,
  ordem de fornecimento ES, ata de registro ES, pregão ES, contrato ES.
  Também dispare quando o usuário fornecer um número de processo do governo
  do ES (formato XXXXXXXX ou XXXX-XXXXX) e pedir para pesquisar publicações.
tools: Bash, Read, Write, Agent
version: 1.0.0
---

# DIO-ES — Pesquisa no Diário Oficial do Espírito Santo

Skill para pesquisa e download de publicações do Diário Oficial do Estado do
Espírito Santo (DIO-ES) via API pública REST. Sem autenticação necessária.

**Repositório:** [github.com/seu-usuario/dio-es-skill](https://github.com)
**API Base:** `https://api.ioes.dio.es.gov.br`
**Cobertura:** Todas as edições digitalizadas do DIO-ES (2000+)

---

## Script

```bash
SCRIPT="$HOME/.claude/skills/dio-es/scripts/dio_search.py"
```

Verificar se funciona:
```bash
python3 $SCRIPT --help
```

---

## API — Referência Rápida

A API do DIO-ES é dividida em 5 aplicações. Esta skill usa 2:

| Aplicação | Base | Uso |
|-----------|------|-----|
| **Transparência** | `/transparencia/v1` | Busca, edições, páginas, download |
| **Busca** | `/busca/v2` | Motor de busca alternativo (multi-diários) |

### Endpoints Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/transparencia/v1/buscas` | GET | Busca por termo com filtro de data |
| `/transparencia/v1/diarios/{id}/edicoes` | GET | Listar edições (filtro por data/número) |
| `/transparencia/v1/diarios/{id}/edicoes/{eid}` | GET | Detalhes de uma edição |
| `/transparencia/v1/diarios/{id}/edicoes/{eid}/paginas/{p}` | GET | Download de página |
| `/transparencia/v1/diarios/{id}/edicoes/{eid}/download` | GET | Download de edição completa |
| `/transparencia/v1/diarios/{id}/edicoes/{eid}/materias` | GET | Listar matérias da edição |
| `/transparencia/v1/diarios/{id}/edicoes/{eid}/materias/{prot}` | GET | Texto completo da matéria |
| `/busca/v2/multidiarios` | GET | Busca alternativa (multi-diários) |

### Parâmetros de Busca (Transparência)

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `termo` | string | **Obrigatório.** Termo de busca |
| `data-inicio` | string | Data início `YYYY-MM-DD` |
| `data-fim` | string | Data fim `YYYY-MM-DD` |
| `limite` | int | Resultados por página (máx 50) |
| `pagina` | int | Página de resultados (0-based) |

### Parâmetros de Busca (v2)

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `q` | string | **Obrigatório.** Termo de busca |
| `data_init` | string | Data início `DD/MM/YYYY` |
| `data_end` | string | Data fim `DD/MM/YYYY` |
| `page` | int | Página (1-based, default 1) |
| `limit` | int | Resultados por página (máx 50) |

### Formatos de Download

| Parâmetro `formato` | Tipo retornado | Uso |
|---------------------|----------------|-----|
| `pdf` | application/pdf | Página ou edição em PDF |
| `imagem` | image/jpeg | Página como imagem JPEG |
| `thumb` | image/jpeg | Miniatura da página |

### IDs dos Diários

| ID | Nome |
|----|------|
| 1 | Diário Oficial dos Poderes do Estado (Executivo) |
| 2 | Diário Oficial dos Municípios |

---

## Quando esta Skill Ativa

**Explícito:** `/dio-es`, "pesquisar no DIO", "buscar no diário oficial"

**Detecção de intenção:**
- "Pesquisa esse processo no DIO"
- "Busca as publicações relacionadas a esse número"
- "Encontra as ordens de fornecimento desse processo"
- "Baixa do diário oficial as licitações da PMES"
- "Procura no DIO-ES por [termo]"
- "Quais publicações existem sobre [assunto] no diário oficial do ES?"
- Números de processo do ES: `80881378`, `2020-1DZ8J`, `86959395`

---

## Fluxo de Trabalho

### Passo 1 — Entender o pedido do usuário

Pergunte ou deduza:
1. **O que buscar?** Número de processo, nome de empresa, tipo de ato, tema
2. **Período?** Datas específicas ou padrão (últimos 5 anos)
3. **Onde salvar?** Pasta de destino (perguntar se não especificado)
4. **Profundidade?** Busca simples ou deep (múltiplos termos cruzados)

### Passo 2 — Definir estratégia de busca

Dependendo do que o usuário forneceu, montar termos de busca:

| Input do usuário | Estratégia |
|------------------|-----------|
| Número de processo (ex: `80881378`) | Buscar direto pelo número |
| Código E-Docs (ex: `2020-1DZ8J`) | Buscar pelo código alfanumérico |
| Nome de empresa (ex: `Glock`) | Combinar com órgão/tipo de ato |
| Tipo de ato (ex: "ordem de fornecimento") | Combinar com órgão/empresa |
| Tema genérico (ex: "pistolas PMES") | Busca ampla + filtragem manual |

**Estratégia Deep Search (recomendada para processos licitatórios):**

Quando o usuário pede pesquisa de um processo de licitação, fazer múltiplas
buscas para cobrir todo o ciclo:

```
Busca 1: Número do processo principal
Busca 2: Número do pregão (ex: "027/2018")
Busca 3: Número da Ata de RP (ex: "045/2018")
Busca 4: Nome da empresa vencedora + órgão
Busca 5: Termos encontrados nos resultados anteriores (OFs, adesões, etc.)
```

Cada resultado pode revelar novos termos. Iterar até esgotar.

### Passo 3 — Executar buscas

**Opção A — Via script (recomendado para buscas simples):**

```bash
# Busca simples com listagem
python3 $SCRIPT search "80881378" --inicio 2018-01-01 --fim 2024-12-31

# Busca e download automático
python3 $SCRIPT download "80881378" -o ./pesquisa_dio --inicio 2018-01-01 --fim 2024-12-31
```

**Opção B — Via curl direto (recomendado para deep search com análise):**

```bash
# Buscar
curl -s "https://api.ioes.dio.es.gov.br/transparencia/v1/buscas?termo=TERMO&data-inicio=2018-01-01&data-fim=2024-12-31&limite=50"

# Obter ID da edição pela data
curl -s "https://api.ioes.dio.es.gov.br/transparencia/v1/diarios/1/edicoes?data=2018-09-11&limite=1"

# Baixar página específica
curl -s -o pagina.pdf "https://api.ioes.dio.es.gov.br/transparencia/v1/diarios/1/edicoes/{EDICAO_ID}/paginas/{PAGINA}?formato=pdf"

# Baixar edição completa
curl -s -o edicao.pdf "https://api.ioes.dio.es.gov.br/transparencia/v1/diarios/1/edicoes/{EDICAO_ID}/download?formato=pdf"
```

**Opção C — Deep search com subagentes (máxima cobertura):**

Para pesquisas complexas, lançar múltiplos subagentes em paralelo:

```
Agent 1: Buscar pelo número do processo principal
Agent 2: Buscar pelo número do pregão + empresa
Agent 3: Buscar pela ata de RP + órgão
```

Consolidar resultados, deduplicar, e baixar.

### Passo 4 — Analisar resultados

Cada resultado da API retorna:

```json
{
  "highlight": "Trecho com <strong>termo</strong> destacado...",
  "protocolo": 425006,
  "edicao_numero": 24816,
  "data": "2018-09-11",
  "pagina": 13,
  "diario": "diario_oficial",
  "suplemento": ""
}
```

Categorizar os resultados por tipo de ato:
- **Aviso de licitação** — publicação do edital
- **Resultado de licitação** — empresa vencedora
- **Ata de Registro de Preços** — resumo da ARP
- **Ordem de Fornecimento** — resumo da OF
- **Contrato** — extrato do contrato
- **Aditivo** — termos aditivos
- **Retificação / Errata** — correções
- **Comunicado** — avisos diversos
- **Adesão** — órgãos aderentes à ARP
- **Portaria / Decreto** — atos normativos
- **Notícia** — matérias jornalísticas (capa do DIO)

### Passo 5 — Baixar páginas

Para cada resultado relevante:

1. **Resolver o edicao_id** a partir da data:
```bash
curl -s "https://api.ioes.dio.es.gov.br/transparencia/v1/diarios/1/edicoes?data=YYYY-MM-DD&limite=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['id'])"
```

2. **Baixar a página correspondente:**
```bash
curl -s -o "ARQUIVO.pdf" \
  "https://api.ioes.dio.es.gov.br/transparencia/v1/diarios/1/edicoes/{EDICAO_ID}/paginas/{PAGINA}?formato=pdf"
```

3. **Nomeação descritiva:**
```
{NN}_{YYYY-MM-DD}_Ed{NUMERO}_p{PAGINA}_{DESCRICAO}.pdf
```
Exemplo: `05_2018-09-11_Ed24816_p13_RESUMO_OF109-2018_GLOCK.pdf`

### Passo 6 — Gerar índice

Sempre gerar um arquivo `INDICE_PESQUISA_DIO.txt` na pasta de destino:

```
==============================================================================
PESQUISA DIO-ES
Termo: "80881378"
Período: 2018-01-01 a 2024-12-31
Data da pesquisa: 23/03/2026 13:39
Total de resultados: 9
==============================================================================

01) 2018-06-18 | Edição 24757 | Página 46 | Protocolo 402833
    Arquivo: 01_2018-06-18_Ed24757_p46_Aviso_Licitacao.pdf
    Trecho: AVISO DE LICITAÇÃO PREGÃO ELETRÔNICO INTERNACIONAL Nº 027/2018...

02) ...
==============================================================================
```

---

## Referência de Comandos (Script)

| Comando | Descrição |
|---------|-----------|
| `python3 $SCRIPT search "termo"` | Listar resultados |
| `python3 $SCRIPT search "termo" --json` | Resultados em JSON |
| `python3 $SCRIPT search "termo" --all --max 200` | Todas as páginas |
| `python3 $SCRIPT download "termo" -o ./pasta` | Buscar + baixar páginas |
| `python3 $SCRIPT download "termo" -o ./pasta --full` | Buscar + baixar edições inteiras |
| `python3 $SCRIPT edition --date 2018-09-11 -o ed.pdf` | Baixar edição por data |
| `python3 $SCRIPT page --date 2018-09-11 --page 13 -o p.pdf` | Baixar página específica |
| `python3 $SCRIPT info --date 2018-09-11` | Info da edição (nº, páginas, etc.) |
| `python3 $SCRIPT materia 425006 --edicao-id 4205` | Texto completo de matéria |

### Flags Globais

| Flag | Descrição |
|------|-----------|
| `--inicio` / `-i` | Data início `YYYY-MM-DD` |
| `--fim` / `-f` | Data fim `YYYY-MM-DD` |
| `--json` | Saída estruturada em JSON |
| `-o` / `--output` | Pasta ou arquivo de destino |

---

## Exemplos de Uso Completos

### Exemplo 1 — Pesquisar processo de licitação

Usuário: "Pesquisa no DIO as publicações do processo 80881378"

```bash
python3 $SCRIPT download "80881378" -o "./pesquisa_80881378" \
  --inicio 2018-01-01 --fim 2024-12-31
```

### Exemplo 2 — Deep search de contrato com empresa

Usuário: "Busca tudo sobre contratos da Glock com a PMES"

Executar múltiplas buscas:
```bash
python3 $SCRIPT search "glock PMES ordem fornecimento" --all --json > /tmp/r1.json
python3 $SCRIPT search "glock PMES contrato" --all --json > /tmp/r2.json
python3 $SCRIPT search "glock PMES ata registro" --all --json > /tmp/r3.json
```
Consolidar, deduplicar, baixar.

### Exemplo 3 — Baixar edição específica

Usuário: "Baixa o DIO do dia 11 de setembro de 2018"

```bash
python3 $SCRIPT edition --date 2018-09-11 -o "./DIO_2018-09-11.pdf"
```

### Exemplo 4 — Baixar página específica

Usuário: "Baixa a página 13 da edição de 11/09/2018"

```bash
python3 $SCRIPT page --date 2018-09-11 --page 13 -o "./pagina_13.pdf"
```

### Exemplo 5 — Pesquisa por texto livre

Usuário: "Procura publicações sobre compra de viaturas pela SESP em 2023"

```bash
python3 $SCRIPT download "viaturas SESP" -o "./pesquisa_viaturas" \
  --inicio 2023-01-01 --fim 2023-12-31
```

---

## Regras de Autonomia

**Executar sem confirmação:**
- `search` — busca é somente leitura
- `info` — informação de edição
- `materia` — leitura de matéria

**Pedir confirmação antes:**
- `download` com muitos resultados (>20 arquivos)
- `edition` (download de edição completa = arquivo grande)
- Criação de pasta no filesystem do usuário

---

## Tratamento de Erros

| Erro | Causa | Solução |
|------|-------|---------|
| HTTP 404 | Edição/página não encontrada | Verificar data/número — feriados não têm edição |
| HTTP 500 | Erro no servidor DIO | Aguardar e tentar novamente |
| Timeout | API lenta | Aumentar timeout ou tentar página individual |
| 0 resultados | Termo não encontrado | Variar termos: aspas, sem acentos, termos parciais |
| Arquivo pequeno (<100B) | Página inexistente naquela edição | Verificar numpag da edição |

### Dicas para Buscas Mais Eficazes

1. **Números de processo** funcionam melhor sem formatação (ex: `80881378`, não `80.881.378`)
2. **Combinar termos** reduz ruído (ex: `"glock PMES"` em vez de só `"glock"`)
3. **Aspas** na API não funcionam como busca exata — use termos combinados
4. **Sem acentos** às vezes retorna mais resultados
5. **Período curto** retorna mais rápido — começar restrito e ampliar se necessário
6. **Feriados e fins de semana** não têm edição — ajustar datas de download
7. Resultados incluem `highlight` com `<strong>` — útil para confirmar relevância

---

## Dependências

- Python 3.6+ (stdlib only — sem pip install)
- `curl` (para downloads diretos via Bash)
- Acesso à internet (API pública, sem autenticação)

---

## Limitações Conhecidas

- API retorna no máximo **50 resultados por página** de busca
- Downloads de edições completas podem ser **grandes** (5-50 MB por edição)
- A busca textual é **full-text** mas não suporta operadores booleanos (AND/OR/NOT)
- Edições muito antigas podem não estar digitalizadas
- Em horários de pico, a API pode responder lentamente
- O campo `protocolo` na busca NÃO é o ID da edição — é o ID da matéria
