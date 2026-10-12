# cardex

Expected-value calculator for Pokémon TCG sealed products. Given a set, a
sealed product (pack/bundle/box), and a retailer's price, it estimates the
expected value of the cards inside and tells you whether the purchase is
financially attractive.

The backend (FastAPI + SQLite) is fully tested and drivable via `/docs` or
`curl`. A minimal React frontend lets you browse sets/products and run a
valuation in the browser. Both can be run locally with `uv`/`npm` or together
via Docker Compose.

## How it works

1. **Ingest**: pull a set's cards + current TCGplayer market prices from
   [carddex.dev](https://carddex.dev)'s free pokemontcg.io v2-compatible API.
2. **Model pack odds**: each set gets a `PullSlot` config (how many cards per
   pack come from which rarity pool). v1 uses a standard modern-era 11-card
   pack template and assumes every card within a rarity pool is equally
   likely to be pulled — a known simplification (see `valuation.py`
   docstring) that will be refined with real community pull-rate data later.
3. **Value a product**: Monte Carlo simulate opening N packs, and report
   expected value, expected profit, ROI%, probability of profit, and
   percentile outcomes (p10/p50/p90) versus the price you paid.
4. **Compare**: rank multiple product/price combos by risk-adjusted return
   (expected profit ÷ std dev), not just raw ROI.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # optional: add a carddex.dev API key for higher rate limits
```

## Usage

```bash
# 1. Pull a set's cards + prices from carddex.dev
uv run cardex sync-sets --name "151"

# 2. See what got synced
uv run cardex list-sets

# 3. Seed standard pull-slot odds + Booster Pack/Bundle/Box products
uv run cardex seed-products

# 4. See the products for a set
uv run cardex list-products sv3pt5

# 5. Run the API
uv run uvicorn cardex.api.app:app --reload
```

Then open http://127.0.0.1:8000/docs and try:

- `GET /api/sets`
- `GET /api/sets/{set_id}/products`
- `POST /api/valuation` with `{"product_id": 1, "retail_price": 4.99}`
- `POST /api/valuation/compare` with multiple `{product_id, retail_price}` items

### Frontend (local dev)

With the API running as above (port 8000):

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default http://localhost:5173) — Vite proxies `/api`
requests to the backend on port 8000.

## Run with Docker

Runs the API and frontend together, with the SQLite database persisted in a
named volume.

```bash
cp .env.example .env   # if you haven't already
docker compose up --build

# in another terminal, once both containers are up:
docker compose exec backend uv run --no-dev cardex sync-sets --name "151"
docker compose exec backend uv run --no-dev cardex seed-products
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Development

```bash
uv run pytest       # unit + API tests (external card API calls are mocked via respx)
uv run ruff check backend/
uv run mypy backend/src/cardex
```

## Known v1 limitations

- Pull odds assume uniform probability within a rarity tier — real packs
  weight secret rares/alt-arts lower than this model does, so EV is likely
  *overstated* for high-end hits.
- The reverse-holo slot reuses each card's canonical market price rather
  than a distinct reverse-holo price point.
- `Product.bonus_card_value` (for things like a guaranteed ETB promo) must be
  set manually; it isn't priced automatically.
