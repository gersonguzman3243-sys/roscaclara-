import pytest


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    """Cada prueba usa su propia carpeta, sin el historial ni la calibración reales."""
    monkeypatch.setenv("ROSCA_DATOS", str(tmp_path))
