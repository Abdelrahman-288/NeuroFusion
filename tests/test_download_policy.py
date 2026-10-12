import ast
from pathlib import Path

import pytest

from neurofusion.download_policy import require_dataset_download


def test_download_policy_rejects_acquisition():
    with pytest.raises(SystemExit, match="downloads are disabled"):
        require_dataset_download()


@pytest.mark.parametrize("name", [
    "download_brisc.py", "download_isles.py", "download_eeg_pilot.py",
    "recover_eeg_download.py", "download_pdgm_metadata.py",
])
def test_acquisition_is_guarded_before_executable_work(name):
    root = Path(__file__).resolve().parents[1]
    body = ast.parse((root / "scripts" / name).read_text(encoding="utf-8")).body
    assert isinstance(body[0], ast.Expr)  # module docstring
    assert isinstance(body[1], ast.ImportFrom)
    assert body[1].module == "neurofusion.download_policy"
    assert isinstance(body[2], ast.Expr)
    assert isinstance(body[2].value, ast.Call)
    assert body[2].value.func.id == "require_dataset_download"
