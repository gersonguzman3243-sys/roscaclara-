import json

import cv2
import numpy as np

from rosca.detector import analizar
from rosca.generar import DIR_EJEMPLOS, EJEMPLOS, generar, pruebas


def _iou(zonas, zona_esperada, shape) -> float:
    if not zona_esperada or not zonas:
        return 0.0
    alto, ancho = shape
    real = np.zeros((alto, ancho), np.uint8)
    predicha = np.zeros((alto, ancho), np.uint8)
    cv2.fillPoly(real, [np.array(zona_esperada, np.int32)], 1)
    for zona in zonas:
        cv2.fillPoly(predicha, [np.array(zona, np.int32)], 1)
    inter = np.logical_and(real, predicha).sum()
    union = np.logical_or(real, predicha).sum()
    return float(inter / union) if union else 0.0


def test_sinteticos_coincidencia_veredicto_tipo_y_zona():
    for espec in pruebas():
        muestra = generar(espec)
        resultado = analizar(muestra.imagen)
        assert resultado.veredicto == muestra.veredicto, espec.id
        if muestra.veredicto == "OK":
            assert resultado.tipo == "ninguno"
            assert resultado.zonas == []
            assert resultado.confianza >= 0.7
        else:
            assert resultado.tipo == espec.tipo, espec.id
            assert _iou(resultado.zonas, muestra.zona, muestra.imagen.shape[:2]) >= 0.45


def test_ejemplos_guardados_siguen_siendo_validos():
    for espec in EJEMPLOS:
        ruta = DIR_EJEMPLOS / f"{espec.id}.jpg"
        etiqueta = json.loads((DIR_EJEMPLOS / f"{espec.id}.json").read_text(encoding="utf-8"))
        imagen = cv2.imdecode(np.frombuffer(ruta.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        resultado = analizar(imagen)
        assert resultado.veredicto == etiqueta["veredicto"]
        assert resultado.tipo == ("ninguno" if etiqueta["tipo"] == "ninguno" else etiqueta["tipo"])


def test_sin_tornillo_no_inventa_veredicto():
    blanco = np.full((480, 720, 3), 230, np.uint8)
    assert analizar(blanco).veredicto == "NO_DETECTADO"
    disco = blanco.copy()
    cv2.circle(disco, (360, 240), 100, (80, 80, 80), -1)
    assert analizar(disco).veredicto == "NO_DETECTADO"


def test_jpeg_no_cambia_un_ok():
    muestra = generar(EJEMPLOS[0])
    ok, buffer = cv2.imencode(".jpg", muestra.imagen, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    assert ok
    imagen = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    assert analizar(imagen).veredicto == "OK"
