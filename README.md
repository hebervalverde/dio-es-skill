# dio-es — Pesquisa no Diário Oficial do Espírito Santo

**Skill para [Claude Code](https://claude.com/claude-code)** que pesquisa e baixa publicações do Diário Oficial do Estado do Espírito Santo (DIO-ES) via API pública.

Sem autenticação. Sem dependências externas. 100% Python stdlib.

---

## O que faz

- Pesquisa publicações por **termo livre** (números de processo, nomes de empresas, tipos de ato, etc.)
- **Baixa automaticamente** as páginas correspondentes do DIO em PDF
- Gera um **índice completo** (`INDICE_PESQUISA_DIO.txt`) com todos os resultados
- Suporta **deep search** — múltiplas buscas cruzadas para cobertura total de processos licitatórios
- Baixa **páginas individuais** ou **edições completas**
- Acessa o **texto completo** de matérias por protocolo

---

## Instalação

### Opção 1 — Clonar para skills do Claude Code

```bash
git clone https://github.com/SEU-USUARIO/dio-es-skill.git ~/.claude/skills/dio-es
```

### Opção 2 — Copiar manualmente

```bash
mkdir -p ~/.claude/skills/dio-es/scripts
# Copiar SKILL.md e scripts/dio_search.py para o diretório
```

Após instalar, a skill aparece automaticamente no Claude Code como `/dio-es`.

---

## Uso

### Via Claude Code (interativo)

Simplesmente peça ao Claude:

```
> Pesquisa no DIO as publicações do processo 80881378
> Busca ordens de fornecimento da Glock com a PMES
> Baixa a página 13 da edição de 11/09/2018
> Procura licitações de viaturas da SESP em 2023
```

A skill será ativada automaticamente quando detectar intenção de pesquisa no DIO-ES.

### Via comando explícito

```
> /dio-es
```

### Via script direto (sem Claude Code)

```bash
SCRIPT=~/.claude/skills/dio-es/scripts/dio_search.py

# Buscar publicações
python3 $SCRIPT search "ordem fornecimento glock PMES"

# Buscar e baixar páginas automaticamente
python3 $SCRIPT download "80881378" -o ./pesquisa_dio --inicio 2018-01-01

# Baixar edição completa por data
python3 $SCRIPT edition --date 2018-09-11 -o ./edicao.pdf

# Baixar página específica
python3 $SCRIPT page --date 2018-09-11 --page 13 -o ./pagina.pdf

# Info de uma edição
python3 $SCRIPT info --date 2018-09-11

# Resultados em JSON
python3 $SCRIPT search "PMES pistola" --json --all --max 100
```

---

## API do DIO-ES

A skill utiliza a API pública REST do DIO-ES:

| Base URL | `https://api.ioes.dio.es.gov.br` |
|----------|----------------------------------|
| Autenticação | Nenhuma (acesso público) |
| Formato | JSON |
| Cobertura | Edições do DIO-ES (2000+) |

### Endpoints utilizados

```
GET /transparencia/v1/buscas              → Busca por termo
GET /transparencia/v1/diarios/{id}/edicoes → Listar edições
GET /transparencia/v1/diarios/{id}/edicoes/{eid} → Detalhes da edição
GET /transparencia/v1/diarios/{id}/edicoes/{eid}/paginas/{p} → Download página
GET /transparencia/v1/diarios/{id}/edicoes/{eid}/download → Download edição
GET /transparencia/v1/diarios/{id}/edicoes/{eid}/materias/{prot} → Texto da matéria
GET /busca/v2/multidiarios                → Motor de busca alternativo
```

### Swagger / Documentação oficial

- [Transparência](https://api.ioes.dio.es.gov.br/transparencia/swagger/)
- [Busca](https://api.ioes.dio.es.gov.br/busca/swagger/)
- [Portal](https://api.ioes.dio.es.gov.br/portal/swagger/)
- [Frontend](https://api.ioes.dio.es.gov.br/frontend/swagger/)
- [Envio](https://api.ioes.dio.es.gov.br/envio/swagger/)

---

## Exemplos de resultado

### Busca simples

```bash
$ python3 dio_search.py search "80881378" --inicio 2018-01-01 --fim 2019-12-31
Total: 9 (mostrando 9)

  1. 2019-08-22 | Ed.25051 p.18 | Prot.513058
     PROCESSO: 80881378 - PMES REFERÊNCIA: Ata de Registro de Preços nº 045/2018...

  2. 2019-08-20 | Ed.25049 p.16 | Prot.513943
     RESUMO DE ORDEM DE FORNECIMENTO Nº 28/2019 PROCESSO: 80881378/PMES...
```

### Download com índice

```bash
$ python3 dio_search.py download "80881378" -o ./pesquisa --inicio 2018-01-01
Buscando: "80881378"...
Encontrados: 9 resultados
Resolvendo 7 edições...
  [1/9] Baixando Ed.25051 p.18 (2019-08-22)...
  [2/9] Baixando Ed.25049 p.16 (2019-08-20)...
  ...
Concluído! 9 arquivos em: ./pesquisa
Índice: ./pesquisa/INDICE_PESQUISA_DIO.txt
```

---

## Estrutura de arquivos

```
~/.claude/skills/dio-es/
├── SKILL.md              ← Definição da skill (Claude Code)
├── README.md             ← Este arquivo
└── scripts/
    └── dio_search.py     ← CLI Python (zero dependências externas)
```

---

## Referência de Comandos

| Comando | Descrição |
|---------|-----------|
| `search "termo"` | Listar resultados da busca |
| `search "termo" --json` | Resultados em JSON |
| `search "termo" --all --max N` | Busca paginada (até N resultados) |
| `download "termo" -o PASTA` | Buscar + baixar páginas |
| `download "termo" -o PASTA --full` | Buscar + baixar edições inteiras |
| `edition --date YYYY-MM-DD -o ARQ` | Baixar edição completa por data |
| `page --date YYYY-MM-DD --page N -o ARQ` | Baixar página específica |
| `info --date YYYY-MM-DD` | Informações da edição |
| `info --date YYYY-MM-DD --json` | Info em JSON |
| `materia PROTOCOLO --edicao-id ID` | Texto completo de matéria |

### Flags

| Flag | Descrição |
|------|-----------|
| `--inicio` / `-i` | Data início `YYYY-MM-DD` |
| `--fim` / `-f` | Data fim `YYYY-MM-DD` |
| `--json` | Saída JSON |
| `--all` / `-a` | Buscar todas as páginas de resultado |
| `--max` | Máximo de resultados (com `--all`) |
| `-o` / `--output` | Destino (pasta ou arquivo) |
| `--full` | Baixar edição completa (não só a página) |

---

## Dicas de busca

1. **Números de processo** sem pontos: `80881378` (não `80.881.378`)
2. **Combine termos** para reduzir ruído: `"glock PMES"` em vez de `"glock"`
3. **Período curto** retorna mais rápido — comece restrito e amplie
4. **Sem acentos** pode retornar mais resultados em alguns casos
5. **Feriados/fins de semana** não têm edição do DIO
6. O campo `protocolo` é o ID da matéria, NÃO o ID da edição

---

## Requisitos

- Python 3.6+
- Nenhuma dependência externa (usa apenas stdlib)
- Acesso à internet
- Claude Code (para uso como skill — opcional, o script funciona standalone)

---

## Licença

MIT

---

## Créditos

- **API DIO-ES:** Departamento de Imprensa Oficial do Estado do Espírito Santo
- **Skill:** Desenvolvida com Claude Code (Anthropic)
