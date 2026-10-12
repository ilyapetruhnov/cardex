from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cardex.api.routes_products import router as products_router
from cardex.api.routes_sets import router as sets_router
from cardex.api.routes_valuation import router as valuation_router
from cardex.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cardex",
        description="Expected-value calculator for Pokémon TCG sealed products",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server (Increment 2)
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sets_router)
    app.include_router(products_router)
    app.include_router(valuation_router)

    return app


app = create_app()
