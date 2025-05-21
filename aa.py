#!/usr/bin/env python3
"""
misp_events_to_csv.py  –  v2
Exporta eventos do MISP com Galaxies, Tags e Correlações → CSV/STDOUT.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Dict, List

import click
from dotenv import load_dotenv
from pymisp import ExpandedPyMISP         # type: ignore
from tabulate import tabulate

# ───────────────────────── Configuração ────────────────────────── #

ENV_PATH = Path(".env")         # MISP_URL e MISP_KEY aqui
DEFAULT_VERIFY_SSL = False

# ---- flags ricos de retorno (incluem Galaxy, Tags, Correl.) ---- #
DEFAULT_FILTERS: Dict[str, Any] = {
    "include_galaxy": True,
    "include_event_tags": True,
    "include_correlations": True,
    "include_context": True,
    "include_sightings": True,
    "sg_reference_only": True,
    # paginação default; pode ser sobrescrita pela CLI
    "page": 1,
    "limit": 500,
}

load_dotenv(ENV_PATH, override=True)


def connect_misp() -> ExpandedPyMISP:
    """Cria a instância ExpandedPyMISP com env vars."""
    return ExpandedPyMISP(
        os.environ["MISP_URL"],
        os.environ["MISP_KEY"],
        ssl=DEFAULT_VERIFY_SSL,
    )


# ────────────────────── Transformação de Evento ────────────────────── #

def flatten_event(raw_evt: Dict[str, Any]) -> Dict[str, Any]:
    """Reduz o JSON do evento às colunas exigidas, lidando com ambos formatos."""
    evt = raw_evt.get("Event", raw_evt)  # desce um nível caso necessário

    clusters = [
        c["value"]
        for g in evt.get("Galaxy", [])
        for c in g.get("GalaxyCluster", [])
    ]

    tags = [t["name"] for t in evt.get("Tag", [])]

    return {
        "Creator org": evt.get("Orgc", {}).get("name", ""),
        "Owner org":   evt.get("Org", {}).get("name", ""),
        "ID":          evt.get("id"),
        "Clusters":    ", ".join(clusters),
        "Tags":        ", ".join(tags),
        "#Attr.":      len(evt.get("Attribute", [])),
        "#Corr.":      evt.get("Attribute_correlation_count", 0),
        "Creator user": evt.get("user", {}).get("email", ""),
        "Date":        evt.get("date"),
        "Info":        evt.get("info"),
        "Distribution": evt.get("distribution"),
    }


# ─────────────────────────── CSV helpers ─────────────────────────── #

def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ CSV salvo em {path.resolve()}")


# ───────────────────────────── CLI ───────────────────────────── #

@click.command()
@click.option("--from", "date_from", help="Data inicial YYYY-MM-DD.")
@click.option("--to", "date_to", help="Data final YYYY-MM-DD.")
@click.option("-o", "--output", type=click.Path(), help="Arquivo CSV de destino.")
@click.option("--page", type=int, default=1, help="Página para paginação.")
@click.option("--limit", type=int, default=500, help="Máximo de eventos por página.")
def main(date_from, date_to, output, page, limit):
    misp = connect_misp()

    # mistura filtros default + argumentos de data/paginação
    filters = DEFAULT_FILTERS | {
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "limit": limit,
    }

    events = misp.search("events", **{k: v for k, v in filters.items() if v is not None})
    rows = [flatten_event(e) for e in events]

    if not rows:
        print("⚠️  Nenhum evento encontrado.")
        return

    if output:
        write_csv(rows, Path(output))
    else:
        print(tabulate(rows, headers="keys", tablefmt="github"))


if __name__ == "__main__":
    main()
