#!/usr/bin/env python3
"""
dio_search.py — CLI tool for searching and downloading from the
Diário Oficial do Estado do Espírito Santo (DIO-ES) public API.

API base: https://api.ioes.dio.es.gov.br
No authentication required — all endpoints are public.

IMPORTANT — Search behavior:
  - Multiple words separated by spaces are treated as OR, not AND.
  - To force exact match, wrap the term in quotes: '"2020-1DZ8J"'
  - E-Docs codes (YYYY-XXXXX) are NOT indexed; use the legacy SEP number.
  - The unique key for a result is (data, edicao_numero, pagina), NOT protocolo.
  - protocolo may repeat across pages of the same edition.

Author: Claude Code / Anthropic
License: MIT
Version: 1.1.0
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ── Constants ────────────────────────────────────────────────────────────────

API_BASE = "https://api.ioes.dio.es.gov.br"
TRANSPARENCIA = f"{API_BASE}/transparencia/v1"
BUSCA = f"{API_BASE}/busca/v2"
DIARIO_ID = 1  # Diário Oficial do ES (Executivo)

# Mapping for known diarios
DIARIOS = {
    "diario_oficial": 1,
    "diario_municipal": 2,
}


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def api_get(url: str, params: dict = None) -> dict:
    """Make a GET request to the API and return parsed JSON."""
    if params:
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "dio-es-search/1.0",
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[ERRO] HTTP {e.code}: {url}", file=sys.stderr)
        if e.code == 404:
            return {}
        raise
    except urllib.error.URLError as e:
        print(f"[ERRO] Conexão falhou: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_file(url: str, dest: str) -> bool:
    """Download a file (PDF/image) from the API."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "dio-es-search/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            if len(data) < 100:
                print(f"  [AVISO] Arquivo muito pequeno ({len(data)} bytes): {dest}", file=sys.stderr)
                return False
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"  [ERRO] Download falhou: {e}", file=sys.stderr)
        return False


# ── Search functions ─────────────────────────────────────────────────────────

def search(termo: str, data_inicio: str = None, data_fim: str = None,
           limite: int = 50, pagina: int = 0) -> dict:
    """
    Search DIO-ES publications using the Transparencia API.

    Args:
        termo: Search term (supports multiple words)
        data_inicio: Start date YYYY-MM-DD (default: 5 years ago)
        data_fim: End date YYYY-MM-DD (default: today)
        limite: Max results per page (max 50)
        pagina: Page number (0-based)

    Returns:
        Dict with 'total' count and 'resultados' list
    """
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    if not data_fim:
        data_fim = datetime.now().strftime("%Y-%m-%d")

    params = {
        "termo": termo,
        "data-inicio": data_inicio,
        "data-fim": data_fim,
        "limite": str(min(limite, 50)),
        "pagina": str(pagina),
    }

    return api_get(f"{TRANSPARENCIA}/buscas", params)


def search_v2(query: str, data_init: str = None, data_end: str = None,
              page: int = 1, limit: int = 50) -> dict:
    """
    Search using the v2 multi-diarios endpoint (alternative search engine).
    Dates in DD/MM/YYYY format.
    """
    params = {
        "q": query,
        "page": str(page),
        "limit": str(min(limit, 50)),
    }
    if data_init:
        params["data_init"] = data_init
    if data_end:
        params["data_end"] = data_end

    return api_get(f"{BUSCA}/multidiarios", params)


def search_all_pages(termo: str, data_inicio: str = None, data_fim: str = None,
                     max_results: int = 200) -> list:
    """
    Search with automatic pagination, collecting up to max_results.
    Returns list of all result dicts.
    """
    all_results = []
    page = 0

    while len(all_results) < max_results:
        data = search(termo, data_inicio, data_fim, limite=50, pagina=page)
        results = data.get("resultados", [])
        total = data.get("total", 0)

        if not results:
            break

        all_results.extend(results)

        if len(all_results) >= total or len(all_results) >= max_results:
            break

        page += 1

    return all_results[:max_results]


# ── Edition functions ────────────────────────────────────────────────────────

def get_edition_by_date(date: str, diario_id: int = DIARIO_ID) -> Optional[dict]:
    """
    Get edition info for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        diario_id: Journal ID (default: 1 = Diário Oficial)

    Returns:
        Edition dict with id, numero, numpag, data, Paginas list, or None
    """
    result = api_get(f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes", {
        "data": date,
        "limite": "1",
    })

    if isinstance(result, list) and result:
        return result[0]
    return None


def get_edition_by_id(edicao_id: int, diario_id: int = DIARIO_ID) -> Optional[dict]:
    """Get full edition details including page list."""
    result = api_get(f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes/{edicao_id}")
    return result if result else None


def list_editions(diario_id: int = DIARIO_ID, data: str = None,
                  edicao: str = None, limite: int = 10) -> list:
    """List editions with optional filters."""
    params = {"limite": str(limite)}
    if data:
        params["data"] = data
    if edicao:
        params["edicao"] = edicao

    result = api_get(f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes", params)
    return result if isinstance(result, list) else []


# ── Materia (article) functions ──────────────────────────────────────────────

def get_materia(protocolo: int, edicao_id: int, diario_id: int = DIARIO_ID) -> dict:
    """Get full text of a specific matéria by its protocol number."""
    return api_get(
        f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes/{edicao_id}/materias/{protocolo}"
    )


def list_materias(edicao_id: int, diario_id: int = DIARIO_ID,
                  cliente_id: str = None, categoria_id: str = None) -> list:
    """List all matérias in an edition."""
    params = {}
    if cliente_id:
        params["cliente_id"] = cliente_id
    if categoria_id:
        params["categoria_id"] = categoria_id

    result = api_get(
        f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes/{edicao_id}/materias", params
    )
    return result if isinstance(result, list) else []


# ── Download functions ───────────────────────────────────────────────────────

def download_page(edicao_id: int, page_num: int, dest: str,
                  formato: str = "pdf", diario_id: int = DIARIO_ID) -> bool:
    """
    Download a specific page from an edition.

    Args:
        edicao_id: Edition ID (not edition number — use get_edition_by_date to resolve)
        page_num: Page number (1-based)
        dest: Destination file path
        formato: 'pdf', 'imagem' (JPEG), or 'thumb'
        diario_id: Journal ID
    """
    url = f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes/{edicao_id}/paginas/{page_num}"
    url += f"?formato={formato}"
    return download_file(url, dest)


def download_edition(edicao_id: int, dest: str, formato: str = "pdf",
                     diario_id: int = DIARIO_ID) -> bool:
    """
    Download a full edition PDF.

    Args:
        edicao_id: Edition ID
        dest: Destination file path
        formato: 'pdf' or 'imagem'
        diario_id: Journal ID
    """
    url = f"{TRANSPARENCIA}/diarios/{diario_id}/edicoes/{edicao_id}/download"
    url += f"?formato={formato}"
    return download_file(url, dest)


# ── High-level workflows ─────────────────────────────────────────────────────

def resolve_edition_id(date: str) -> Optional[int]:
    """Convert a date string (YYYY-MM-DD) to an edition ID."""
    ed = get_edition_by_date(date)
    return ed["id"] if ed else None


def search_and_download(termo: str, output_dir: str,
                        data_inicio: str = None, data_fim: str = None,
                        download_pages: bool = True,
                        download_full_editions: bool = False,
                        max_results: int = 200) -> list:
    """
    Complete workflow: search, collect results, download pages/editions.

    Args:
        termo: Search term
        output_dir: Directory to save downloaded files
        data_inicio: Start date YYYY-MM-DD
        data_fim: End date YYYY-MM-DD
        download_pages: Download individual matching pages (default True)
        download_full_editions: Download full edition PDFs instead of pages
        max_results: Maximum number of results to process

    Returns:
        List of result dicts augmented with download paths
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Buscando: \"{termo}\"...")
    results = search_all_pages(termo, data_inicio, data_fim, max_results)
    print(f"Encontrados: {len(results)} resultados")

    if not results:
        return []

    # Deduplicate by (date, page)
    seen = set()
    unique = []
    for r in results:
        key = (r["data"], r["pagina"], r.get("suplemento", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    results = unique

    # Resolve edition IDs (batch by date)
    date_to_edicao = {}
    dates_needed = set(r["data"] for r in results)

    print(f"Resolvendo {len(dates_needed)} edições...")
    for date in sorted(dates_needed):
        eid = resolve_edition_id(date)
        if eid:
            date_to_edicao[date] = eid
        else:
            print(f"  [AVISO] Edição não encontrada para {date}", file=sys.stderr)

    # Download
    downloaded = []
    for i, r in enumerate(results, 1):
        date = r["data"]
        page = r["pagina"]
        ed_num = r["edicao_numero"]
        protocolo = r.get("protocolo", "")
        edicao_id = date_to_edicao.get(date)

        if not edicao_id:
            continue

        # Build descriptive filename
        highlight_clean = strip_html(r.get("highlight", ""))[:80]
        highlight_slug = slugify(highlight_clean)

        if download_full_editions:
            fname = f"{i:02d}_{date}_Ed{ed_num}_COMPLETO.pdf"
            fpath = os.path.join(output_dir, fname)
            if not os.path.exists(fpath):
                print(f"  [{i}/{len(results)}] Baixando edição {ed_num} ({date})...")
                ok = download_edition(edicao_id, fpath)
            else:
                ok = True
        else:
            fname = f"{i:02d}_{date}_Ed{ed_num}_p{page:02d}_{highlight_slug[:50]}.pdf"
            fpath = os.path.join(output_dir, fname)
            if not os.path.exists(fpath):
                print(f"  [{i}/{len(results)}] Baixando Ed.{ed_num} p.{page} ({date})...")
                ok = download_page(edicao_id, page, fpath)
            else:
                ok = True

        r["_arquivo"] = fname if ok else None
        r["_edicao_id"] = edicao_id
        downloaded.append(r)

    # Generate index
    index_path = os.path.join(output_dir, "INDICE_PESQUISA_DIO.txt")
    generate_index(termo, results, index_path, data_inicio, data_fim)

    print(f"\nConcluído! {len(downloaded)} arquivos em: {output_dir}")
    print(f"Índice: {index_path}")

    return downloaded


def generate_index(termo: str, results: list, dest: str,
                   data_inicio: str = None, data_fim: str = None):
    """Generate a human-readable index file for search results."""
    lines = [
        "=" * 78,
        f"PESQUISA DIO-ES",
        f"Termo: \"{termo}\"",
        f"Período: {data_inicio or 'N/A'} a {data_fim or 'N/A'}",
        f"Data da pesquisa: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Total de resultados: {len(results)}",
        "=" * 78,
        "",
    ]

    for i, r in enumerate(results, 1):
        date = r["data"]
        page = r["pagina"]
        ed_num = r["edicao_numero"]
        protocolo = r.get("protocolo", "")
        highlight = strip_html(r.get("highlight", ""))[:300]
        arquivo = r.get("_arquivo", "N/A")

        lines.append(f"{i:02d}) {date} | Edição {ed_num} | Página {page} | Protocolo {protocolo}")
        lines.append(f"    Arquivo: {arquivo}")
        lines.append(f"    Trecho: {highlight}")
        lines.append("")

    lines.append("=" * 78)

    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Categorization ───────────────────────────────────────────────────────────

CATEGORY_PATTERNS = [
    ("AVISO_LICITACAO",      [r"aviso de licita", r"aviso de preg", r"torna p.blico.*far. realizar"]),
    ("RESULTADO_LICITACAO",  [r"resultado de licita", r"resultado.*preg.o", r"situa..o final do lote"]),
    ("ATA_RP",               [r"ata de registro de pre", r"resumo da ata"]),
    ("ADITIVO_ARP",          [r"aditivo.*ata de registro", r"termo aditivo.*ata"]),
    ("ORDEM_FORNECIMENTO",   [r"ordem de fornecimento", r"resumo.*ordem.*fornec"]),
    ("CONTRATO",             [r"extrato de contrato", r"resumo.*contrato", r"contrato n"]),
    ("ADESAO",               [r"ades.o.*ata", r"aviso de ades", r"solicita.*ades.o", r"carona"]),
    ("DOACAO",               [r"doa..o", r"termo de doa", r"contrato de doa"]),
    ("RETIFICACAO",          [r"retifica", r"errata", r"onde se l.", r"leia.se"]),
    ("COMUNICADO_JUDICIAL",  [r"liminar", r"sobrestado", r"decis.o.*judicial"]),
    ("EMPENHO",              [r"nota de empenho", r"empenho n"]),
    ("HOMOLOGACAO",          [r"homologa..o", r"homologar"]),
    ("NOTICIA",              [r"governo.*entrega", r"recebeu.*pistola", r"investimento.*seguran"]),
    ("TREINAMENTO",          [r"curso.*glock", r"treinamento.*pistola", r"capacita..o.*arma"]),
    ("TCE_DENUNCIA",         [r"den.ncia.*tce", r"tribunal de contas"]),
]


def categorize_result(highlight: str) -> str:
    """Categorize a search result based on keyword patterns in the highlight."""
    text = strip_html(highlight).lower()
    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text):
                return category
    return "OUTROS"


# ── Utility functions ────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[àáâãäå]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:60]


def format_results_json(results: list) -> str:
    """Format results as JSON for machine consumption."""
    clean = []
    for r in results:
        entry = {
            "data": r["data"],
            "pagina": r["pagina"],
            "edicao_numero": r["edicao_numero"],
            "protocolo": r.get("protocolo"),
            "diario": r.get("diario", "diario_oficial"),
            "suplemento": r.get("suplemento", ""),
            "highlight": strip_html(r.get("highlight", "")),
            "arquivo": r.get("_arquivo"),
            "edicao_id": r.get("_edicao_id"),
        }
        if "_categoria" in r:
            entry["categoria"] = r["_categoria"]
        clean.append(entry)
    return json.dumps(clean, indent=2, ensure_ascii=False)


def format_results_table(results: list) -> str:
    """Format results as a readable table."""
    lines = []
    for i, r in enumerate(results, 1):
        date = r["data"]
        page = r["pagina"]
        ed = r["edicao_numero"]
        prot = r.get("protocolo", "")
        hl = strip_html(r.get("highlight", ""))[:120]
        lines.append(f"{i:3d}. {date} | Ed.{ed} p.{page:2d} | Prot.{prot}")
        lines.append(f"     {hl}...")
        lines.append("")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pesquisa e download do Diário Oficial do ES (DIO-ES)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Busca simples (apenas listar)
  python3 dio_search.py search "ordem fornecimento glock"

  # Busca e download de páginas
  python3 dio_search.py download "80881378" -o ./pesquisa_dio

  # Busca com período específico
  python3 dio_search.py search "pregão 027/2018" --inicio 2018-01-01 --fim 2019-12-31

  # Download de edição completa por data
  python3 dio_search.py edition --date 2018-09-11 -o ./edicao.pdf

  # Download de página específica por data
  python3 dio_search.py page --date 2018-09-11 --page 13 -o ./pagina.pdf

  # Busca com saída JSON
  python3 dio_search.py search "PMES pistola" --json

  # Busca paginada (todas as páginas)
  python3 dio_search.py search "glock" --all --max 100
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando")

    # ── search ───────────────────────────────────────────────────────────
    sp_search = subparsers.add_parser("search", help="Buscar publicações por termo")
    sp_search.add_argument("termo", help="Termo de busca")
    sp_search.add_argument("--inicio", "-i", help="Data início (YYYY-MM-DD)")
    sp_search.add_argument("--fim", "-f", help="Data fim (YYYY-MM-DD)")
    sp_search.add_argument("--limite", "-l", type=int, default=50, help="Limite por página (max 50)")
    sp_search.add_argument("--pagina", "-p", type=int, default=0, help="Página (0-based)")
    sp_search.add_argument("--all", "-a", action="store_true", help="Buscar todas as páginas")
    sp_search.add_argument("--max", type=int, default=200, help="Máx. resultados (com --all)")
    sp_search.add_argument("--json", action="store_true", help="Saída em JSON")
    sp_search.add_argument("--exact", "-e", action="store_true",
                           help="Busca exata (envolve o termo em aspas)")
    sp_search.add_argument("--categorize", action="store_true",
                           help="Categorizar resultados por tipo de ato")

    # ── download ─────────────────────────────────────────────────────────
    sp_dl = subparsers.add_parser("download", help="Buscar e baixar páginas/edições")
    sp_dl.add_argument("termo", help="Termo de busca")
    sp_dl.add_argument("-o", "--output", required=True, help="Pasta de destino")
    sp_dl.add_argument("--inicio", "-i", help="Data início (YYYY-MM-DD)")
    sp_dl.add_argument("--fim", "-f", help="Data fim (YYYY-MM-DD)")
    sp_dl.add_argument("--full", action="store_true", help="Baixar edições completas (não só páginas)")
    sp_dl.add_argument("--max", type=int, default=200, help="Máx. resultados")
    sp_dl.add_argument("--json", action="store_true", help="Saída em JSON ao final")

    # ── edition ──────────────────────────────────────────────────────────
    sp_ed = subparsers.add_parser("edition", help="Baixar edição completa por data ou número")
    sp_ed.add_argument("--date", "-d", help="Data da edição (YYYY-MM-DD)")
    sp_ed.add_argument("--id", type=int, help="ID da edição (direto)")
    sp_ed.add_argument("--numero", "-n", type=int, help="Número da edição")
    sp_ed.add_argument("-o", "--output", required=True, help="Arquivo de destino (.pdf)")

    # ── page ─────────────────────────────────────────────────────────────
    sp_pg = subparsers.add_parser("page", help="Baixar página específica de uma edição")
    sp_pg.add_argument("--date", "-d", help="Data da edição (YYYY-MM-DD)")
    sp_pg.add_argument("--edicao-id", type=int, help="ID da edição (direto)")
    sp_pg.add_argument("--page", "-p", type=int, required=True, help="Número da página")
    sp_pg.add_argument("-o", "--output", required=True, help="Arquivo de destino (.pdf)")
    sp_pg.add_argument("--formato", choices=["pdf", "imagem", "thumb"], default="pdf")

    # ── info ─────────────────────────────────────────────────────────────
    sp_info = subparsers.add_parser("info", help="Informações sobre uma edição")
    sp_info.add_argument("--date", "-d", help="Data da edição (YYYY-MM-DD)")
    sp_info.add_argument("--id", type=int, help="ID da edição")
    sp_info.add_argument("--json", action="store_true", help="Saída em JSON")

    # ── materia ──────────────────────────────────────────────────────────
    sp_mat = subparsers.add_parser("materia", help="Obter texto completo de uma matéria")
    sp_mat.add_argument("protocolo", type=int, help="Número do protocolo")
    sp_mat.add_argument("--edicao-id", type=int, required=True, help="ID da edição")
    sp_mat.add_argument("--json", action="store_true", help="Saída em JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # ── Execute commands ─────────────────────────────────────────────────

    if args.command == "search":
        termo = f'"{args.termo}"' if args.exact else args.termo
        if args.all:
            results = search_all_pages(termo, args.inicio, args.fim, args.max)
        else:
            data = search(termo, args.inicio, args.fim, args.limite, args.pagina)
            results = data.get("resultados", [])
            total = data.get("total", 0)
            if not args.json:
                print(f"Total: {total} (mostrando {len(results)})\n")

        if hasattr(args, 'categorize') and args.categorize:
            for r in results:
                r["_categoria"] = categorize_result(r.get("highlight", ""))

        if args.json:
            print(format_results_json(results))
        else:
            print(format_results_table(results))

    elif args.command == "download":
        results = search_and_download(
            args.termo,
            args.output,
            args.inicio,
            args.fim,
            download_pages=not args.full,
            download_full_editions=args.full,
            max_results=args.max,
        )
        if args.json:
            print(format_results_json(results))

    elif args.command == "edition":
        edicao_id = args.id
        if not edicao_id and args.date:
            edicao_id = resolve_edition_id(args.date)
        if not edicao_id and args.numero:
            eds = list_editions(edicao=str(args.numero))
            if eds:
                edicao_id = eds[0]["id"]

        if not edicao_id:
            print("[ERRO] Edição não encontrada", file=sys.stderr)
            sys.exit(1)

        print(f"Baixando edição {edicao_id}...")
        if download_edition(edicao_id, args.output):
            print(f"Salvo: {args.output}")
        else:
            sys.exit(1)

    elif args.command == "page":
        edicao_id = args.edicao_id
        if not edicao_id and args.date:
            edicao_id = resolve_edition_id(args.date)

        if not edicao_id:
            print("[ERRO] Edição não encontrada", file=sys.stderr)
            sys.exit(1)

        print(f"Baixando página {args.page} da edição {edicao_id}...")
        if download_page(edicao_id, args.page, args.output, args.formato):
            print(f"Salvo: {args.output}")
        else:
            sys.exit(1)

    elif args.command == "info":
        ed = None
        if args.id:
            ed = get_edition_by_id(args.id)
        elif args.date:
            ed = get_edition_by_date(args.date)

        if not ed:
            print("[ERRO] Edição não encontrada", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(ed, indent=2, ensure_ascii=False))
        else:
            print(f"ID:       {ed.get('id')}")
            print(f"Número:   {ed.get('numero')}")
            print(f"Data:     {ed.get('data')}")
            print(f"Título:   {ed.get('titulo')}")
            print(f"Páginas:  {ed.get('numpag')}")
            print(f"Diário:   {ed.get('diario')}")

    elif args.command == "materia":
        ed_id = args.edicao_id
        mat = get_materia(args.protocolo, ed_id)

        if not mat:
            print("[ERRO] Matéria não encontrada", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(mat, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(mat, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
