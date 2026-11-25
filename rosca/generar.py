"""Genera tornillos sintéticos de perfil, con cuerda sana o defectuosa.

Las imágenes no sustituyen fotos de taller: sirven para probar la app y las
pruebas automáticas sin un banco de fotos reales. La cuerda se dibuja como
la vería una cámara de lado, con los dientes de arriba y abajo desfasados
(como en una hélice de verdad).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
DIR_EJEMPLOS = RAIZ / "ejemplos"


def _diente(fase: float) -> float:
    """Onda triangular: 1 en la cresta, 0 en la raíz."""
    f = fase % 1.0
    return 1.0 - abs(2.0 * f - 1.0)


@dataclass(frozen=True)
class Espec:
    id: str
    semilla: int
    tipo: str = "ninguno"  # ninguno, barrida, incompleta, danada, mal_formada
    inicio: float = 0.38
    fin: float = 0.68
    angulo: float | None = None
    escala: float | None = None
    fondo: str = "claro"  # claro | oscuro
    titulo: str = ""

    @property
    def veredicto(self) -> str:
        return "OK" if self.tipo == "ninguno" else "DEFECTUOSO"


@dataclass
class Muestra:
    imagen: np.ndarray
    id: str
    titulo: str
    veredicto: str
    tipo: str
    zona: list[list[float]] | None
    semilla: int


def _aplicar_defecto(
    r_top: np.ndarray,
    r_bot: np.ndarray,
    a: int,
    b: int,
    tipo: str,
    crest_r: float,
    root_r: float,
    pitch: float,
    fase0: float,
    desfase: float,
    rng: np.random.Generator,
    fases: np.ndarray | None = None,
) -> None:
    altura = crest_r - root_r
    if tipo == "barrida":
        # Sigue habiendo paso, pero la cresta quedó aplastada.
        for x in range(a, b):
            fase = float(fases[x]) if fases is not None else fase0 + (x - a) / pitch
            r_top[x] = root_r + altura * _diente(fase) * 0.40
            r_bot[x] = root_r + altura * _diente(fase + desfase) * 0.40
        return
    if tipo == "incompleta":
        r_top[a:b] = root_r + altura * 0.03
        r_bot[a:b] = root_r + altura * 0.03
        return
    if tipo == "danada":
        # Se caen dientes sueltos: quedan huecos de uno o dos pasos, no un tramo liso largo.
        if fases is None:
            fases = fase0 + (np.arange(len(r_top)) - a) / pitch
        ids = np.floor(fases[a:b] + 1e-6).astype(int)
        for n, did in enumerate(sorted(set(ids.tolist()))):
            if n % 3 == 2:
                continue
            sel = a + np.where(ids == did)[0]
            r_top[sel] = root_r + altura * 0.04
            r_bot[sel] = root_r + altura * 0.04
        return
    if tipo == "mal_formada":
        paso_malo = pitch * float(rng.uniform(1.85, 2.15))
        fase = fase0
        for x in range(a, b):
            r_top[x] = root_r + altura * _diente(fase) * 0.92
            r_bot[x] = root_r + altura * _diente(fase + desfase) * 0.92
            fase += 1.0 / paso_malo
        return
    raise ValueError(f"Tipo de defecto desconocido: {tipo}")


def _perfiles(espec: Espec, rng: np.random.Generator, escala: float):
    diam = 96.0 * escala
    crest_r = diam / 2.0
    root_r = crest_r * 0.80
    pitch = diam * 0.15
    head_r = crest_r * 1.38
    head_len = int(diam * 0.92)
    tip_len = int(diam * 0.78)
    thread_len = int(diam * float(rng.uniform(4.7, 5.5)))
    length = head_len + thread_len + tip_len

    r_top = np.zeros(length, dtype=np.float64)
    r_bot = np.zeros(length, dtype=np.float64)
    tip_start = length - tip_len
    desfase = float(rng.uniform(0.46, 0.54))
    fase = float(rng.uniform(0.0, 1.0))
    fases = np.zeros(length, dtype=np.float64)
    for x in range(length):
        fases[x] = fase
        fase += (1.0 + float(rng.uniform(-0.025, 0.025))) / pitch
    amps = 1.0 + rng.uniform(-0.035, 0.035, size=length)

    for x in range(length):
        if x < head_len - 5:
            factor = 0.80 + 0.20 * min(x, 12) / 12.0
            radio = head_r * factor
            # Arandela justo antes del cuerpo.
            if head_len - 14 <= x < head_len - 5:
                radio = head_r * 1.06
            r_top[x] = radio
            r_bot[x] = radio
        elif x < head_len:
            k = (x - (head_len - 5)) / 5.0
            radio = head_r * (1.0 - k) + crest_r * k
            r_top[x] = radio
            r_bot[x] = radio
        elif x >= tip_start:
            k = (x - tip_start) / max(1, tip_len)
            radio = max(2.0, crest_r * (1.0 - 0.92 * k))
            r_top[x] = radio
            r_bot[x] = radio
        else:
            alt = crest_r - root_r
            r_top[x] = root_r + alt * _diente(fases[x]) * amps[x]
            r_bot[x] = root_r + alt * _diente(fases[x] + desfase) * amps[x]

    zona_x = None
    if espec.tipo != "ninguno":
        a = int(head_len + espec.inicio * thread_len)
        b = int(head_len + espec.fin * thread_len)
        b = max(b, a + int(pitch * 3))
        b = min(b, tip_start - 1)
        _aplicar_defecto(
            r_top,
            r_bot,
            a,
            b,
            espec.tipo,
            crest_r,
            root_r,
            pitch,
            float(fases[a]),
            desfase,
            rng,
            fases,
        )
        zona_x = (a, b)

    return {
        "r_top": r_top,
        "r_bot": r_bot,
        "length": length,
        "head_len": head_len,
        "tip_start": tip_start,
        "crest_r": crest_r,
        "root_r": root_r,
        "pitch": pitch,
        "head_r": head_r,
        "zona_x": zona_x,
    }


def _fondo(ancho: int, alto: int, rng: np.random.Generator, modo: str) -> np.ndarray:
    yy, xx = np.mgrid[0:alto, 0:ancho]
    if modo == "oscuro":
        base = np.array([38, 36, 34], dtype=np.float32)
        viñeta = 10.0
    else:
        calor = float(rng.uniform(-6, 8))
        base = np.array([214 - calor * 0.2, 218 + calor * 0.15, 224 + calor], dtype=np.float32)
        viñeta = 16.0
    img = np.ones((alto, ancho, 3), dtype=np.float32) * base
    # Grano suave y una viñeta leve para que no parezca un recorte plano.
    ruido = rng.normal(0, 2.4 if modo == "claro" else 1.6, size=img.shape)
    cx, cy = ancho / 2, alto / 2
    d = np.sqrt(((xx - cx) / ancho) ** 2 + ((yy - cy) / alto) ** 2)
    img += ruido
    img -= viñeta * np.clip(d - 0.25, 0, 1)[..., None]
    return np.clip(img, 0, 255)


def _sombra(img: np.ndarray, mask: np.ndarray, modo: str) -> None:
    if modo != "claro":
        return
    h, w = mask.shape
    desplazada = np.zeros_like(mask)
    dy = 14
    desplazada[dy:, :] = mask[:-dy, :]
    blur = cv2.GaussianBlur(desplazada, (41, 41), 9)
    libre = mask == 0
    factor = np.ones((h, w), dtype=np.float32)
    factor[libre] -= 0.10 * (blur[libre].astype(np.float32) / 255.0)
    img *= factor[..., None]


def generar(espec: Espec) -> Muestra:
    rng = np.random.default_rng(espec.semilla)
    escala = float(espec.escala) if espec.escala else float(rng.uniform(0.9, 1.12))
    geo = _perfiles(espec, rng, escala)
    r_top = geo["r_top"]
    r_bot = geo["r_bot"]
    length = geo["length"]
    margen = 28
    local_w = length + margen * 2
    local_h = int(geo["head_r"] * 2 + margen * 2 + 16)
    cy = local_h / 2.0

    angulo = float(espec.angulo) if espec.angulo is not None else float(rng.uniform(-5.2, 5.2))
    ancho, alto = 1080, 640
    dest_x = ancho / 2.0 + float(rng.uniform(-36, 36))
    dest_y = alto / 2.0 + float(rng.uniform(-28, 28))
    matriz = cv2.getRotationMatrix2D((local_w / 2.0, local_h / 2.0), angulo, 1.0)
    matriz[0, 2] += dest_x - local_w / 2.0
    matriz[1, 2] += dest_y - local_h / 2.0
    inversa = cv2.invertAffineTransform(matriz)

    img = _fondo(ancho, alto, rng, espec.fondo)
    esquinas = np.array(
        [[0, 0], [local_w, 0], [local_w, local_h], [0, local_h]], dtype=np.float32
    )
    unos = np.ones((4, 1), dtype=np.float32)
    proyectadas = np.hstack([esquinas, unos]) @ matriz.T
    x0 = max(0, int(np.floor(proyectadas[:, 0].min())) - 2)
    x1 = min(ancho, int(np.ceil(proyectadas[:, 0].max())) + 3)
    y0 = max(0, int(np.floor(proyectadas[:, 1].min())) - 2)
    y1 = min(alto, int(np.ceil(proyectadas[:, 1].max())) + 3)

    yy, xx = np.mgrid[y0:y1, x0:x1]
    xl = inversa[0, 0] * xx + inversa[0, 1] * yy + inversa[0, 2]
    yl = inversa[1, 0] * xx + inversa[1, 1] * yy + inversa[1, 2]
    sx = xl - margen
    indice = np.clip(np.rint(sx).astype(np.int32), 0, length - 1)
    dentro_largo = (sx >= 0) & (sx < length - 0.5)
    rt = r_top[indice]
    rb = r_bot[indice]
    # yl crece hacia abajo; la cresta de arriba queda en cy - r_top.
    borde_sup = cy - rt
    borde_inf = cy + rb
    inside = dentro_largo & (yl >= borde_sup) & (yl <= borde_inf)

    firmado = np.zeros(xx.shape, dtype=np.float64)
    radio_local = np.maximum((rt + rb) / 2.0, 1.0)
    np.divide(yl - cy, radio_local, out=firmado, where=inside)
    diente_rel = np.clip((rt - geo["root_r"]) / (geo["crest_r"] - geo["root_r"] + 1e-6), 0, 1.2)

    if espec.fondo == "oscuro":
        tono = 176 + 52 * np.exp(-((firmado - 0.18) ** 2) / 0.10)
        tono += 10 * (1 - np.abs(firmado))
        tono -= 26 * (1 - np.clip(diente_rel, 0, 1))
        tono = np.clip(tono, 148, 236)
    else:
        tono = 86 + 50 * np.exp(-((firmado - 0.20) ** 2) / 0.11)
        tono += 12 * (1 - np.abs(firmado))
        tono -= 24 * (1 - np.clip(diente_rel, 0, 1))
        tono = np.clip(tono, 58, 156)

    # Ranuras del hexágono, solo en la cabeza, para que se lea como tornillo.
    cabeza = inside & (sx < geo["head_len"] - 5)
    for ranura in (geo["head_len"] * 0.34, geo["head_len"] * 0.66):
        tono = np.where(cabeza, tono - 16 * np.exp(-((sx - ranura) ** 2) / 10.0), tono)

    tono = np.clip(tono + rng.normal(0, 1.7, size=tono.shape), 0, 255)
    if espec.fondo == "oscuro":
        b = np.clip(tono + 4, 0, 255)
        g = tono
        r = np.clip(tono - 5, 0, 255)
    else:
        b = np.clip(tono + 7, 0, 255)
        g = tono
        r = np.clip(tono - 5, 0, 255)
    color = np.stack([b, g, r], axis=-1).astype(np.float32)
    region = img[y0:y1, x0:x1]
    region[inside] = color[inside]
    img[y0:y1, x0:x1] = region

    mask = np.zeros((alto, ancho), dtype=np.uint8)
    mask[y0:y1, x0:x1][inside] = 255
    _sombra(img, mask, espec.fondo)
    salida = np.clip(img, 0, 255).astype(np.uint8)
    salida = cv2.GaussianBlur(salida, (3, 3), 0.45)

    zona = None
    if geo["zona_x"] is not None:
        a, b = geo["zona_x"]
        pad = 3.0
        y_sup = cy - float(np.maximum(r_top[a:b], r_bot[a:b]).max()) - pad
        y_inf = cy + float(np.maximum(r_top[a:b], r_bot[a:b]).max()) + pad
        locales = np.array(
            [
                [a + margen, y_sup],
                [b + margen, y_sup],
                [b + margen, y_inf],
                [a + margen, y_inf],
            ],
            dtype=np.float64,
        )
        hom = np.hstack([locales, np.ones((4, 1))])
        zona = (hom @ matriz.T).tolist()

    titulo = espec.titulo or espec.id.replace("-", " ").capitalize()
    return Muestra(
        imagen=salida,
        id=espec.id,
        titulo=titulo,
        veredicto=espec.veredicto,
        tipo=espec.tipo,
        zona=zona,
        semilla=espec.semilla,
    )


EJEMPLOS: list[Espec] = [
    Espec("ejemplo-01", 11, "ninguno", angulo=-3.4, escala=1.0, titulo="Ejemplo 1"),
    Espec("ejemplo-02", 18, "ninguno", angulo=2.2, escala=0.94, titulo="Ejemplo 2"),
    Espec("ejemplo-03", 27, "ninguno", angulo=-1.1, escala=1.08, titulo="Ejemplo 3"),
    Espec("ejemplo-04", 36, "ninguno", angulo=4.4, escala=1.02, titulo="Ejemplo 4"),
    Espec("ejemplo-05", 42, "barrida", inicio=0.40, fin=0.66, angulo=-2.6, escala=1.0, titulo="Ejemplo 5"),
    Espec("ejemplo-06", 53, "incompleta", inicio=0.28, fin=0.52, angulo=1.8, escala=0.96, titulo="Ejemplo 6"),
    Espec("ejemplo-07", 64, "danada", inicio=0.46, fin=0.74, angulo=-4.2, escala=1.06, titulo="Ejemplo 7"),
    Espec("ejemplo-08", 75, "mal_formada", inicio=0.34, fin=0.70, angulo=3.1, escala=1.0, titulo="Ejemplo 8"),
]


def pruebas() -> list[Espec]:
    """Casos más amplios que la galería, para las pruebas automáticas."""
    casos = [
        Espec("ok-a", 101, "ninguno", angulo=-5.0, escala=0.9),
        Espec("ok-b", 102, "ninguno", angulo=5.0, escala=1.12),
        Espec("ok-c", 103, "ninguno", angulo=0.4, escala=1.0),
        Espec("ok-d", 104, "ninguno", angulo=-2.2, escala=0.95, fondo="oscuro"),
        Espec("ok-e", 105, "ninguno", angulo=3.3, escala=1.05),
        Espec("ok-f", 106, "ninguno", angulo=-0.8, escala=1.0),
        Espec("barrida-a", 201, "barrida", 0.42, 0.70, angulo=-3.0, escala=1.0),
        Espec("barrida-b", 202, "barrida", 0.22, 0.48, angulo=4.0, escala=0.92, fondo="oscuro"),
        Espec("barrida-total", 203, "barrida", 0.02, 0.98, angulo=1.0, escala=1.0),
        Espec("incompleta-a", 301, "incompleta", 0.30, 0.55, angulo=2.5, escala=1.04),
        Espec("incompleta-b", 302, "incompleta", 0.50, 0.78, angulo=-4.5, escala=0.93),
        Espec("danada-a", 401, "danada", 0.36, 0.62, angulo=-1.5, escala=1.0),
        Espec("danada-b", 402, "danada", 0.48, 0.80, angulo=3.6, escala=1.08, fondo="oscuro"),
        Espec("mal-a", 501, "mal_formada", 0.33, 0.64, angulo=-2.8, escala=1.0),
        Espec("mal-b", 502, "mal_formada", 0.40, 0.78, angulo=1.4, escala=0.96),
    ]
    casos.extend(EJEMPLOS)
    return casos


def guardar_ejemplos(directorio: Path | None = None) -> list[Path]:
    directorio = directorio or DIR_EJEMPLOS
    directorio.mkdir(parents=True, exist_ok=True)
    rutas = []
    manifiesto = []
    for espec in EJEMPLOS:
        muestra = generar(espec)
        ruta = directorio / f"{espec.id}.jpg"
        cv2.imwrite(str(ruta), muestra.imagen, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        etiqueta = {
            "id": muestra.id,
            "titulo": muestra.titulo,
            "veredicto": muestra.veredicto,
            "tipo": muestra.tipo,
            "zona": muestra.zona,
        }
        (directorio / f"{espec.id}.json").write_text(
            json.dumps(etiqueta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifiesto.append({"id": muestra.id, "titulo": muestra.titulo})
        rutas.append(ruta)
    (directorio / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return rutas


if __name__ == "__main__":
    rutas = guardar_ejemplos()
    print(f"Se guardaron {len(rutas)} ejemplos en {DIR_EJEMPLOS}")
