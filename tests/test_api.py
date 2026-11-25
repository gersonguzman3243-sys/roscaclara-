import cv2
from fastapi.testclient import TestClient

from rosca.api import app
from rosca.generar import EJEMPLOS, generar


def test_ejemplos_e_inspeccion_quedan_en_el_historial():
    cliente = TestClient(app)
    ejemplos = cliente.get("/api/ejemplos")
    assert ejemplos.status_code == 200
    assert len(ejemplos.json()["ejemplos"]) == 8

    muestra = generar(EJEMPLOS[4])  # defectuoso, cuerda barrida
    ok, buffer = cv2.imencode(".jpg", muestra.imagen)
    assert ok
    respuesta = cliente.post(
        "/api/inspeccionar",
        files={"archivo": ("ejemplo-barrida.jpg", buffer.tobytes(), "image/jpeg")},
        data={"origen": "ejemplo", "nombre": "Ejemplo barrido", "guardar": "true"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["veredicto"] == "DEFECTUOSO"
    assert cuerpo["tipo"] == "barrida"
    assert cuerpo["zonas"]
    assert cuerpo["imagen_jpeg"]
    assert cuerpo["id_historial"]

    historial = cliente.get("/api/historial").json()
    assert historial["resumen"]["total"] == 1
    assert historial["resumen"]["defectuosos"] == 1
    assert historial["resumen"]["porcentaje_defectuosos"] == 100
    assert historial["items"][0]["nombre"] == "Ejemplo barrido"

    mini = cliente.get(f"/api/historial/{cuerpo['id_historial']}/miniatura")
    assert mini.status_code == 200
    assert mini.headers["content-type"].startswith("image/jpeg")

    csv = cliente.get("/api/historial.csv")
    assert csv.status_code == 200
    texto = csv.content.decode("utf-8-sig")
    assert "DEFECTUOSO" in texto
    assert "Ejemplo barrido" in texto

    assert cliente.delete("/api/historial").status_code == 200
    assert cliente.get("/api/historial").json()["resumen"]["total"] == 0


def test_no_guarda_si_no_hay_tornillo():
    cliente = TestClient(app)
    import numpy as np

    blanco = np.full((360, 640, 3), 225, np.uint8)
    ok, buffer = cv2.imencode(".jpg", blanco)
    assert ok
    respuesta = cliente.post(
        "/api/inspeccionar",
        files={"archivo": ("vacio.jpg", buffer.tobytes(), "image/jpeg")},
        data={"origen": "subida", "nombre": "vacio"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["veredicto"] == "NO_DETECTADO"
    assert respuesta.json()["id_historial"] is None
    assert cliente.get("/api/historial").json()["resumen"]["total"] == 0
