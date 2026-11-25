import json

import cv2

from rosca.calibrar import calibrar
from rosca.detector import analizar
from rosca.generar import Espec, generar


def _guardar(directorio, espec):
    directorio.mkdir(parents=True, exist_ok=True)
    muestra = generar(espec)
    cv2.imwrite(str(directorio / f"{espec.id}.jpg"), muestra.imagen)


def test_calibrar_separa_buenos_y_defectuosos(tmp_path):
    buenos = tmp_path / "buenos"
    malos = tmp_path / "defectuosos"
    for i, semilla in enumerate((11, 18, 27, 36, 101, 102)):
        _guardar(buenos, Espec(f"b{i}", semilla, "ninguno", angulo=(-1) ** i * 2.0))
    for i, (semilla, tipo) in enumerate(
        ((42, "barrida"), (53, "incompleta"), (64, "danada"), (75, "mal_formada"))
    ):
        _guardar(
            malos,
            Espec(f"m{i}", semilla, tipo, inicio=0.34, fin=0.7, angulo=1.5),
        )

    config = calibrar(buenos, malos, tmp_path / "calibracion.json")
    assert 0.3 <= config["umbral"] <= 0.85
    assert config["n_buenos"] == 6
    assert config["n_defectuosos"] == 4
    assert config["youden"] >= 0.9

    guardada = json.loads((tmp_path / "calibracion.json").read_text(encoding="utf-8"))
    assert guardada["origen"] == "propia"

    # Con ese corte, las mismas fotos siguen del lado correcto.
    for ruta in sorted(buenos.glob("*.jpg")):
        imagen = cv2.imread(str(ruta))
        assert analizar(imagen, umbral=config["umbral"]).veredicto == "OK"
    for ruta in sorted(malos.glob("*.jpg")):
        imagen = cv2.imread(str(ruta))
        assert analizar(imagen, umbral=config["umbral"]).veredicto == "DEFECTUOSO"


def test_calibrar_exige_minimo_de_buenos(tmp_path):
    buenos = tmp_path / "buenos"
    _guardar(buenos, Espec("solo", 11, "ninguno"))
    try:
        calibrar(buenos, tmp_path / "defectuosos", tmp_path / "calibracion.json")
    except ValueError as error:
        assert "al menos 5" in str(error)
    else:
        raise AssertionError("debía pedir más fotos buenas")
