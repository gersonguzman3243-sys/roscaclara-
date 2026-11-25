"""Lectura de fotos, sin depender del nombre del archivo."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def listar_imagenes(directorio: Path) -> list[Path]:
    if not directorio.exists():
        return []
    return sorted(
        ruta
        for ruta in directorio.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES
    )


def cargar(ruta: Path) -> np.ndarray:
    datos = np.frombuffer(ruta.read_bytes(), dtype=np.uint8)
    imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError(f"No pude abrir {ruta.name}")
    return imagen


def decodificar(contenido: bytes) -> np.ndarray:
    datos = np.frombuffer(contenido, dtype=np.uint8)
    imagen = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError("Ese archivo no parece una imagen. Usa JPG o PNG.")
    return imagen


def a_jpeg(imagen: np.ndarray, calidad: int = 86) -> bytes:
    ok, buffer = cv2.imencode(".jpg", imagen, [int(cv2.IMWRITE_JPEG_QUALITY), calidad])
    if not ok:
        raise ValueError("No pude preparar la imagen.")
    return buffer.tobytes()


def miniatura(imagen: np.ndarray, ancho: int = 280) -> bytes:
    alto_orig, ancho_orig = imagen.shape[:2]
    alto = max(1, int(round(alto_orig * (ancho / max(ancho_orig, 1)))))
    chica = cv2.resize(imagen, (ancho, alto), interpolation=cv2.INTER_AREA)
    return a_jpeg(chica, calidad=80)
