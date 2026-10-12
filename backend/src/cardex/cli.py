from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from cardex.db import get_session_factory, init_db
from cardex.models import Product, Set
from cardex.seed_data import seed_set
from cardex.sync import sync_sets_by_name

app = typer.Typer(help="Cardex: ingest Pokémon TCG data and manage sealed-product definitions.")
console = Console()


@app.command("sync-sets")
def sync_sets(
    name: str = typer.Option(..., "--name", help='Search text, e.g. "151" or "Prismatic"'),
) -> None:
    """Search carddex.dev for sets matching NAME and upsert them + their cards."""
    init_db()
    session = get_session_factory()()
    try:
        matches = sync_sets_by_name(session, name)
        if not matches:
            console.print(f"[yellow]No sets found matching '{name}'[/yellow]")
            raise typer.Exit(code=1)
        for set_ in matches:
            console.print(
                f"[green]Synced[/green] {set_.id}: {set_.name} ({set_.total_cards} cards)"
            )
    finally:
        session.close()


@app.command("seed-products")
def seed_products(
    set_id: str | None = typer.Option(
        None, "--set-id", help="Seed only this set id. Omit to seed all synced sets."
    ),
) -> None:
    """Create standard pull-slot config + Booster Pack/Bundle/Box products."""
    init_db()
    session = get_session_factory()()
    try:
        set_ids = [set_id] if set_id else [row[0] for row in session.query(Set.id).all()]
        if not set_ids:
            console.print("[yellow]No sets in the database yet — run sync-sets first.[/yellow]")
            raise typer.Exit(code=1)
        for sid in set_ids:
            seed_set(session, sid)
            console.print(f"[green]Seeded[/green] products + pull slots for {sid}")
    finally:
        session.close()


@app.command("list-sets")
def list_sets() -> None:
    """Show all sets currently in the database."""
    init_db()
    session = get_session_factory()()
    try:
        table = Table("Set ID", "Name", "Series", "Released", "Cards")
        for set_ in session.query(Set).order_by(Set.release_date.desc()).all():
            table.add_row(set_.id, set_.name, set_.series, set_.release_date, str(set_.total_cards))
        console.print(table)
    finally:
        session.close()


@app.command("list-products")
def list_products(set_id: str = typer.Argument(..., help="Set id, e.g. sv3pt5")) -> None:
    """Show products configured for a set."""
    init_db()
    session = get_session_factory()()
    try:
        table = Table("ID", "Name", "Type", "Packs/Product", "Bonus Value")
        products = session.query(Product).filter(Product.set_id == set_id).all()
        for product in products:
            table.add_row(
                str(product.id),
                product.name,
                product.product_type,
                str(product.packs_per_product),
                str(product.bonus_card_value),
            )
        console.print(table)
    finally:
        session.close()


if __name__ == "__main__":
    app()
