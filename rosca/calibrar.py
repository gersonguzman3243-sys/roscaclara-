"""Ajusta el umbral con las fotos del usuario.

Lee datos/buenos y, si hay, datos/defectuosos. Guarda datos/calibracion.json.
El puntaje de cada foto sale del mismo detector; aquí solo se mueve el
corte entre OK y DEFECTUOSO.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from rosca.detector import analizar, directorio_datos
from rosca.imagenes import cargar, listar_imagenes


def calibrar(
    buenos: Path | None = None,
    defectuosos: Path | None = None,
    destino: Path | None = None,
) -> dict:
    datos = directorio_datos()
    dir_buenos = buenos or (datos / "buenos")
    dir_malos = defectuosos or (datos / "defectuosos")
    salida = destino or (datos / "calibracion.json")

    fotos_buenas = listar_imagenes(dir_buenos)
    if len(fotos_buenas) < 5:
        raise ValueError(
            "Hacen falta al menos 5 fotos de tornillos buenos en datos/buenos. "
            f"Ahora hay {len(fotos_buenas)}."
        )

    ok_scores, omitidas = _puntajes(fotos_buenas)
    if len(ok_scores) < 5:
        raise ValueError(
            "Varias fotos de datos/buenos no se pudieron leer como tornillo de lado. "
            "Revisa el encuadre: perfil, fondo que contraste, cuerda a la vista."
        )

    media = float(np.mean(ok_scores))
    desviacion = float(np.std(ok_scores))
    umbral = float(np.clip(media + 2.5 * desviacion, 0.35, 0.8))
    metodo = "Solo tornillos buenos: el corte queda en la media más 2.5 desviaciones."
    youden = None

    fotos_malas = listar_imagenes(dir_malos)
    mal_scores: list[float] = []
    if len(fotos_malas) >= 3:
        mal_scores, omitidas_mal = _puntajes(fotos_malas)
        omitidas += omitidas_mal
        if len(mal_scores) >= 3:
            umbral, youden = _youden(ok_scores, mal_scores)
            metodo = (
                "Con buenos y defectuosos se eligió el corte que mejor separa los dos grupos "
                f"(índice de Youden {youden:.2f})."
            )

    config = {
        "umbral": round(umbral, 4),
        "altura_minima_rel": 0.034,
        "origen": "propia",
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_buenos": len(ok_scores),
        "n_defectuosos": len(mal_scores),
        "n_omitidas": omitidas,
        "puntaje_bueno_medio": round(media, 4),
        "youden": None if youden is None else round(youden, 4),
        "metodo": metodo,
        "nota": (
            "Este umbral sale de tus fotos, con el mismo encuadre en el que las tomaste. "
            "No predice cómo irá con otra luz o con otro tipo de tornillo."
        ),
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def _puntajes(rutas: list[Path]) -> tuple[list[float], int]:
    puntajes = []
    omitidas = 0
    for ruta in rutas:
        try:
            imagen = cargar(ruta)
        except ValueError:
            omitidas += 1
            continue
        resultado = analizar(imagen)
        if resultado.veredicto == "NO_DETECTADO":
            omitidas += 1
            continue
        puntajes.append(float(resultado.puntaje))
    return puntajes, omitidas


def _youden(ok_scores: list[float], mal_scores: list[float]) -> tuple[float, float]:
    mejor_t = 0.5
    mejor_j = -2.0
    for umbral in np.linspace(0.2, 0.85, 66):
        sensibilidad = float(np.mean([s >= umbral for s in mal_scores]))
        especificidad = float(np.mean([s < umbral for s in ok_scores]))
        j = sensibilidad + especificidad - 1.0
        if j > mejor_j + 1e-9:
            mejor_j = j
            mejor_t = float(umbral)
    return float(np.clip(mejor_t, 0.3, 0.85)), mejor_j


if __name__ == "__main__":
    resultado = calibrar()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
