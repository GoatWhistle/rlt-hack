from contextlib import asynccontextmanager

from src.application.encoder import text_encoder
from src.application.supplier_index import supplier_index
from src.service.search.supplier import SupplierSearch


@asynccontextmanager
async def supplier_search():
    async with (
        supplier_index() as index,
        text_encoder(dimensions=index.dimensions, context_length=256) as encoder,
    ):
        yield SupplierSearch(index, encoder)
