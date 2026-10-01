import runpy
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
SCRIPTS = (
    "normalizer/normalizer_smoke.py",
    "classifier/classifier_smoke.py",
    "supplier/enrich_smoke.py",
    "supplier/identity_smoke.py",
    "supplier/reidentify_smoke.py",
)


@pytest.mark.parametrize("script", SCRIPTS)
def test_smoke_script_passes(script: str, capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(TESTS / script), run_name="__main__")
    assert capsys.readouterr().out.strip()
