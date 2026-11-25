"""API y, si ya está construida, la interfaz web."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from rosca import __version__
from rosca.calibrar import calibrar
from rosca.detector import _preparar, analizar, cargar_configuracion, directorio_datos
from rosca.generar import DIR_EJEMPLOS
from rosca.historial import a_csv, agregar, listar, miniatura as leer_miniatura, resumen, vaciar
from rosca.imagenes import a_jpeg, decodificar, miniatura

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "web" / "dist"
MAX_BYTES = 12 * 1024 * 1024

app = FastAPI(title="RoscaClara", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> Path:
    return directorio_datos() / "historial.sqlite"


def _asegurar_carpetas() -> None:
    datos = directorio_datos()
    (datos / "buenos").mkdir(parents=True, exist_ok=True)
    (datos / "defectuosos").mkdir(parents=True, exist_ok=True)


@app.get("/api/salud")
def salud() -> dict:
    _asegurar_carpetas()
    config = cargar_configuracion()
    return {
        "nombre": "RoscaClara",
        "version": __version__,
        "umbral": config.get("umbral"),
        "origen_umbral": "propia" if (directorio_datos() / "calibracion.json").exists() else "fabrica",
    }


@app.get("/api/ejemplos")
def ejemplos() -> dict:
    manifiesto = DIR_EJEMPLOS / "manifiesto.json"
    if not manifiesto.exists():
        return {"ejemplos": []}
    import json

    lista = json.loads(manifiesto.read_text(encoding="utf-8"))
    return {
        "ejemplos": [
            {
                "id": item["id"],
                "titulo": item["titulo"],
                "url": f"/api/ejemplos/{item['id']}.jpg",
            }
            for item in lista
        ]
    }


@app.get("/api/ejemplos/{nombre}")
def ejemplo_archivo(nombre: str) -> FileResponse:
    if "/" in nombre or ".." in nombre:
        raise HTTPException(404, "No encontré ese ejemplo.")
    ruta = (DIR_EJEMPLOS / nombre).resolve()
    if not ruta.is_file() or ruta.parent != DIR_EJEMPLOS.resolve():
        raise HTTPException(404, "No encontré ese ejemplo.")
    return FileResponse(ruta, media_type="image/jpeg")


@app.post("/api/inspeccionar")
async def inspeccionar(
    archivo: UploadFile = File(...),
    origen: str = Form("subida"),
    nombre: str = Form(""),
    guardar: bool = Form(True),
) -> dict:
    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, "La foto pesa más de 12 MB. Prueba con una más chica.")
    if not contenido:
        raise HTTPException(400, "La imagen llegó vacía.")
    try:
        imagen = decodificar(contenido)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    preparada = _preparar(imagen)
    resultado = analizar(preparada, ya_preparada=True)
    jpeg = a_jpeg(preparada)
    id_historial = None
    if guardar and resultado.veredicto in {"OK", "DEFECTUOSO"}:
        _asegurar_carpetas()
        id_historial = agregar(
            _db(),
            veredicto=resultado.veredicto,
            confianza=resultado.confianza,
            puntaje=resultado.puntaje,
            tipo=resultado.tipo,
            explicacion=resultado.explicacion,
            origen=origen if origen in {"subida", "camara", "ejemplo"} else "subida",
            nombre=(nombre or archivo.filename or "tornillo").strip()[:120],
            miniatura_jpeg=miniatura(preparada),
        )
    cuerpo = resultado.a_dict()
    cuerpo["imagen_jpeg"] = base64.b64encode(jpeg).decode("ascii")
    cuerpo["id_historial"] = id_historial
    return cuerpo


@app.get("/api/historial")
def obtener_historial() -> dict:
    ruta = _db()
    return {"resumen": resumen(ruta), "items": listar(ruta)}


@app.get("/api/historial/{id_inspeccion}/miniatura")
def obtener_miniatura(id_inspeccion: int) -> Response:
    datos = leer_miniatura(_db(), id_inspeccion)
    if datos is None:
        raise HTTPException(404, "Esa revisión ya no está en el historial.")
    return Response(content=datos, media_type="image/jpeg")


@app.delete("/api/historial")
def borrar_historial() -> dict:
    vaciar(_db())
    return {"ok": True}


@app.get("/api/historial.csv")
def exportar_historial() -> Response:
    texto = "\ufeff" + a_csv(_db())
    return Response(
        content=texto,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="historial-rosca.csv"'},
    )


@app.get("/api/calibracion")
def obtener_calibracion() -> dict:
    config = cargar_configuracion()
    propia = (directorio_datos() / "calibracion.json").exists()
    return {
        "umbral": config.get("umbral"),
        "origen": "propia" if propia else "fabrica",
        "n_buenos": config.get("n_buenos", 0),
        "n_defectuosos": config.get("n_defectuosos", 0),
        "creado": config.get("creado"),
        "metodo": config.get("metodo")
        or "Umbral de fábrica, afinado con los tornillos de ejemplo. No mide fotos de taller.",
    }


@app.post("/api/calibrar")
def recalibrar() -> dict:
    _asegurar_carpetas()
    try:
        return calibrar()
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/")
def inicio() -> FileResponse:
    indice = DIST / "index.html"
    if indice.exists():
        return FileResponse(indice)
    raise HTTPException(
        503,
        "La interfaz todavía no está construida. En desarrollo corre npm run dev dentro de web/.",
    )


@app.get("/{ruta:path}")
def estaticos(ruta: str) -> FileResponse:
    if ruta.startswith("api"):
        raise HTTPException(404, "No encontré esa ruta.")
    if not DIST.exists():
        raise HTTPException(503, "La interfaz todavía no está construida.")
    candidato = (DIST / ruta).resolve()
    raiz = DIST.resolve()
    if candidato.is_file() and raiz in candidato.parents:
        return FileResponse(candidato)
    indice = DIST / "index.html"
    if indice.exists():
        return FileResponse(indice)
    raise HTTPException(404, "No encontré ese archivo.")
