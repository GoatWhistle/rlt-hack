import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.adapter.client.errors import RegistryDumpError
from src.adapter.client.msp_registry.dump import MspRegistryDump
from tests.registry.fixtures import DOCUMENTS, write_zip


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", [False, True])
async def test_dump_opens_zip_once_and_closes_after_success_or_failure(
    tmp_path: Path, broken: bool
) -> None:
    path = write_zip(
        tmp_path / "registry.zip", {"a.xml": DOCUMENTS, "b.xml": "<" if broken else DOCUMENTS}
    )
    constructor = zipfile.ZipFile
    opened: list[zipfile.ZipFile] = []

    def capture(location: Path) -> zipfile.ZipFile:
        archive = constructor(location)
        opened.append(archive)
        return archive

    with patch("src.adapter.client.msp_registry.dump.zipfile.ZipFile", side_effect=capture):
        if broken:
            with pytest.raises(RegistryDumpError):
                _ = [batch async for batch in MspRegistryDump(path).read()]
        else:
            batches = [batch async for batch in MspRegistryDump(path).read()]
            assert len(batches) == 2
            assert batches[0] == batches[1]
    assert len(opened) == 1
    assert opened[0].fp is None


@pytest.mark.asyncio
async def test_consumer_can_close_dump_between_files(tmp_path: Path) -> None:
    path = write_zip(tmp_path / "registry.zip", {"a.xml": DOCUMENTS, "b.xml": DOCUMENTS})
    archive = zipfile.ZipFile(path)
    with patch("src.adapter.client.msp_registry.dump.zipfile.ZipFile", return_value=archive):
        iterator = MspRegistryDump(path).read()
        assert await anext(iterator)
        await iterator.aclose()
    assert archive.fp is None
