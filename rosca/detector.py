"""Lee la cuerda de un tornillo visto de lado y marca tramos defectuosos.

No usa una red neuronal. Busca el tornillo por contraste, endereza el perfil
con el eje mayor y revisa cada borde (arriba y abajo) como una onda de
dientes. Un diente sano se parece a los demás en altura y en paso. Un tramo
barrido, incompleto, mordido o con el paso cambiado se sale de ese ritmo.

Los umbrales de fábrica salen de los tornillos sintéticos incluidos. Con
fotos reales hay que recalibrar: la exactitud en taller no está medida.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
DIR_PAQUETE = Path(__file__).resolve().parent

# Referencia geométrica de una cuerda métrica vista de lado:
# la altura del diente ronda un 6–10 % del diámetro. Sirve de arranque;
# la calibración del usuario la puede sustituir.
PRIORS = {
    "altura_minima_rel": 0.034,
    "umbral": 0.50,
}


@dataclass
class Resultado:
    veredicto: str
    confianza: float
    puntaje: float
    tipo: str
    explicacion: str
    zonas: list[list[list[float]]]
    contorno: list[list[float]]
    ancho: int
    alto: int
    detalle: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return {
            "veredicto": self.veredicto,
            "confianza": round(float(self.confianza), 4),
            "puntaje": round(float(self.puntaje), 4),
            "tipo": self.tipo,
            "explicacion": self.explicacion,
            "zonas": self.zonas,
            "contorno": self.contorno,
            "ancho": self.ancho,
            "alto": self.alto,
            "detalle": self.detalle,
        }


def directorio_datos() -> Path:
    return Path(os.environ.get("ROSCA_DATOS", RAIZ / "datos"))


def cargar_configuracion() -> dict:
    config = dict(PRIORS)
    base = DIR_PAQUETE / "calibracion_base.json"
    if base.exists():
        config.update(json.loads(base.read_text(encoding="utf-8")))
    propia = directorio_datos() / "calibracion.json"
    if propia.exists():
        config.update(json.loads(propia.read_text(encoding="utf-8")))
    return config


def _suavizar(senal: np.ndarray, sigma: float) -> np.ndarray:
    senal = np.asarray(senal, dtype=np.float32)
    if len(senal) < 5:
        return senal.copy()
    sigma = float(max(sigma, 0.8))
    k = int(sigma * 6) | 1
    k = max(3, min(k, max(3, (len(senal) // 2) * 2 - 1)))
    if k % 2 == 0:
        k += 1
    pad = k
    extendida = np.pad(senal, pad, mode="edge")
    borrosa = cv2.GaussianBlur(extendida.reshape(1, -1), (k, 1), sigmaX=sigma)
    return borrosa.ravel()[pad:-pad]


def _correlacion(a: np.ndarray, b: np.ndarray) -> float:
    a = a - float(np.mean(a))
    b = b - float(np.mean(b))
    d = float(np.linalg.norm(a) * np.linalg.norm(b))
    if d < 1e-6:
        return 0.0
    return float(np.dot(a, b) / d)


def _estimar_paso(onda: np.ndarray) -> int | None:
    """Paso típico entre crestas.

    La mediana de los espacios cortos ignora un tramo defectuoso (ahí las
    crestas se alejan o desaparecen) y no se deja llevar por el doble del paso.
    """
    onda = np.asarray(onda, dtype=np.float64)
    if len(onda) < 36:
        return None
    pp = float(np.percentile(onda, 98) - np.percentile(onda, 2))
    if pp < 1.3:
        return None
    picos = _picos(onda, distancia=8, prominencia=max(pp * 0.22, 0.75))
    if len(picos) < 4:
        return None
    dists = np.diff(np.array(picos))
    limite = float(np.percentile(dists, 55))
    cortos = dists[dists <= max(limite, 10)]
    if len(cortos) < 3:
        cortos = dists
    paso = int(round(float(np.median(cortos))))
    if paso < 8:
        return None
    return paso


def _picos(senal: np.ndarray, distancia: int, prominencia: float) -> list[int]:
    encontrados: list[int] = []
    n = len(senal)
    distancia = max(1, distancia)
    for i in range(1, n - 1):
        if senal[i] < prominencia:
            continue
        if senal[i] < senal[i - 1] or senal[i] < senal[i + 1]:
            continue
        if not encontrados or i - encontrados[-1] >= distancia:
            encontrados.append(i)
        elif senal[i] > senal[encontrados[-1]]:
            encontrados[-1] = i
    return encontrados


def _tramo_mas_largo(mascara: np.ndarray) -> tuple[int, int] | None:
    mejor = None
    inicio = None
    for i, valor in enumerate(mascara):
        if valor and inicio is None:
            inicio = i
        if not valor and inicio is not None:
            if mejor is None or i - inicio > mejor[1] - mejor[0]:
                mejor = (inicio, i)
            inicio = None
    if inicio is not None:
        fin = len(mascara)
        if mejor is None or fin - inicio > mejor[1] - mejor[0]:
            mejor = (inicio, fin)
    return mejor


def _mascara(bgr: np.ndarray) -> np.ndarray | None:
    gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    _, umbral = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mejor = None
    mejor_puntaje = 0.0
    for candidato in (umbral, cv2.bitwise_not(umbral)):
        nlab, etiquetas, stats, _ = cv2.connectedComponentsWithStats(candidato, 8)
        if nlab <= 1:
            continue
        areas = stats[1:, cv2.CC_STAT_AREA]
        indice = 1 + int(np.argmax(areas))
        area = int(stats[indice, cv2.CC_STAT_AREA])
        if area < 900:
            continue
        mask = np.where(etiquetas == indice, 255, 0).astype(np.uint8)
        mask = _rellenar_huecos(mask)
        ys, xs = np.where(mask)
        if len(xs) < 900:
            continue
        pts = np.column_stack((xs, ys)).astype(np.float64)
        cov = np.cov((pts - pts.mean(0)).T)
        valores = np.linalg.eigvalsh(cov)
        alargado = float(valores[-1] / (valores[0] + 1e-6))
        fraccion = area / mask.size
        if fraccion > 0.72 or fraccion < 0.012 or alargado < 6:
            continue
        if alargado > mejor_puntaje:
            mejor_puntaje = alargado
            mejor = mask
    return mejor


def _rellenar_huecos(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    inundada = mask.copy()
    marcador = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(inundada, marcador, (0, 0), 255)
    huecos = cv2.bitwise_not(inundada)
    return cv2.bitwise_or(mask, huecos)


def _perfil(mask: np.ndarray):
    ys, xs = np.where(mask > 0)
    pts = np.column_stack((xs, ys)).astype(np.float64)
    media = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - media, full_matrices=False)
    eje = vt[0]
    perpendicular = np.array([-eje[1], eje[0]])
    u = (pts - media) @ eje
    v = (pts - media) @ perpendicular
    u_min = float(u.min())
    bins = np.floor(u - u_min).astype(np.int32)
    nb = int(bins.max()) + 1
    superior = np.full(nb, np.inf)
    inferior = np.full(nb, -np.inf)
    np.minimum.at(superior, bins, v)
    np.maximum.at(inferior, bins, v)
    vacios = ~np.isfinite(superior) | (superior == np.inf)
    idx = np.arange(nb)
    buenos = ~vacios
    if int(buenos.sum()) < 40:
        return None
    superior = np.interp(idx, idx[buenos], superior[buenos])
    inferior = np.interp(idx, idx[buenos], inferior[buenos])
    grosor = inferior - superior
    return {
        "media": media,
        "eje": eje,
        "perpendicular": perpendicular,
        "u_min": u_min,
        "superior": superior,
        "inferior": inferior,
        "grosor": grosor,
    }


def _poligono(perfil: dict, b0: int, b1: int, pad: float = 3.0) -> list[list[float]]:
    n = len(perfil["superior"])
    b0 = int(np.clip(b0, 0, n - 1))
    b1 = int(np.clip(b1, b0 + 1, n))
    v0 = float(np.min(perfil["superior"][b0:b1])) - pad
    v1 = float(np.max(perfil["inferior"][b0:b1])) + pad
    u0 = perfil["u_min"] + b0
    u1 = perfil["u_min"] + b1
    puntos = []
    for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
        xy = perfil["media"] + perfil["eje"] * u + perfil["perpendicular"] * v
        puntos.append([round(float(xy[0]), 2), round(float(xy[1]), 2)])
    return puntos


def _region_de_cuerda(grosor: np.ndarray) -> tuple[int, int] | None:
    mediana = float(np.median(grosor))
    es_cuerpo = (grosor <= mediana * 1.16) & (grosor >= mediana * 0.72)
    tramo = _tramo_mas_largo(es_cuerpo)
    if tramo is None:
        return None
    a, b = tramo
    if b - a < 40:
        return None
    # El extremo más delgado, fuera del cuerpo, es la punta: se recorta más.
    izq = float(np.mean(grosor[max(0, a - 12) : a])) if a > 4 else mediana
    der = float(np.mean(grosor[b : min(len(grosor), b + 12)])) if b < len(grosor) - 4 else mediana
    recorte = max(8, int((b - a) * 0.035))
    if izq < der:
        a += int(recorte * 1.7)
        b -= recorte
    else:
        a += recorte
        b -= int(recorte * 1.7)
    if b - a < 36:
        return None
    return a, b


def _analizar_borde(
    onda: np.ndarray,
    paso: int,
    diametro: float,
    altura_minima_rel: float,
) -> dict:
    pp = float(np.percentile(onda, 98) - np.percentile(onda, 2))
    rel = pp / (diametro + 1e-6)
    if rel < altura_minima_rel * 0.85 or pp < 1.4:
        return {
            "puntaje": 0.93,
            "tipo": "barrida",
            "tramos": [(0, len(onda), 0.93, "barrida")],
            "rel": rel,
            "dientes": 0,
        }

    dist = max(3, int(paso * 0.62))
    prominencia = max(pp * 0.16, 0.7)
    picos = _picos(onda, dist, prominencia)
    if len(picos) < 3:
        return {
            "puntaje": 0.88,
            "tipo": "incompleta",
            "tramos": [(0, len(onda), 0.88, "incompleta")],
            "rel": rel,
            "dientes": len(picos),
        }

    cortes = picos
    segmentos = []
    margen = int(paso * 0.45)
    for izq, der in zip(cortes[:-1], cortes[1:]):
        if der - izq < max(3, int(paso * 0.55)):
            continue
        # El primer y el último diente suelen quedar cortados por la cabeza o la punta.
        if izq < margen or der > len(onda) - margen:
            continue
        segmentos.append((izq, der))

    if len(segmentos) < 3:
        return {
            "puntaje": 0.12,
            "tipo": "ninguno",
            "tramos": [],
            "rel": rel,
            "dientes": len(picos),
            "muestras": [],
        }

    alturas = []
    largos = []
    formas = []
    for izq, der in segmentos:
        pedazo = onda[izq:der]
        alturas.append(float(np.percentile(pedazo, 95) - np.percentile(pedazo, 5)))
        largos.append(der - izq)
        muestra = np.interp(np.linspace(0, len(pedazo) - 1, 24), np.arange(len(pedazo)), pedazo)
        formas.append(muestra - np.mean(muestra))
    alturas_a = np.array(alturas)
    largos_a = np.array(largos, dtype=np.float64)
    formas_a = np.stack(formas)
    # La referencia sale de los dientes más altos: así un tramo malo
    # no arrastra consigo el patrón de lo que se considera sano.
    ref_altura = float(np.percentile(alturas_a, 80))
    ref_largo = float(np.median(largos_a))
    # Si TODOS los dientes están bajos, no hay una parte sana con qué comparar.
    if float(np.median(alturas_a)) / (diametro + 1e-6) < 0.046:
        return {
            "puntaje": 0.91,
            "tipo": "barrida",
            "tramos": [(0, len(onda) - 1, 0.91, "barrida")],
            "rel": rel,
            "dientes": len(picos),
            "muestras": [],
        }
    normas = np.linalg.norm(formas_a, axis=1)
    orden = np.argsort(normas)
    nucleo = formas_a[orden[len(orden) // 2 :]]
    plantilla = np.median(nucleo, axis=0)
    norma_p = float(np.linalg.norm(plantilla))

    def correlacion(forma: np.ndarray) -> float:
        d = float(np.linalg.norm(forma) * norma_p)
        if d < 1e-6:
            return 0.0
        return float(np.dot(forma, plantilla) / d)

    tramos = []
    muestras = []
    for (izq, der), altura, largo, forma in zip(segmentos, alturas, largos, formas_a):
        rel_h = altura / (diametro + 1e-6)
        rel_l = largo / (ref_largo + 1e-6)
        corr = correlacion(forma)
        plano = float(np.clip((0.85 * ref_altura - altura) / (0.85 * ref_altura + 1e-6), 0, 1))
        hueco = float(np.clip((rel_l - 1.45) / 0.7, 0, 1))
        paso_raro = float(np.clip((abs(rel_l - 1.0) - 0.34) / 0.5, 0, 1))
        forma_rara = 0.0
        if rel_h >= altura_minima_rel:
            forma_rara = float(np.clip((0.58 - corr) / 0.58, 0, 1))

        # En un hueco largo se mira el centro, sin las crestas sanas de las orillas.
        rel_interior = rel_h
        if rel_l >= 1.7 and der - izq > paso:
            i0 = izq + int(0.18 * (der - izq))
            i1 = der - int(0.18 * (der - izq))
            nucleo = onda[i0:i1] if i1 > i0 + 3 else onda[izq:der]
            rel_interior = float(np.percentile(nucleo, 95) - np.percentile(nucleo, 5)) / (diametro + 1e-6)

        if rel_l >= 1.55 and rel_interior < altura_minima_rel * 1.45:
            # Hueco corto: se perdieron uno o dos dientes (cuerda dañada).
            # Hueco largo y liso: cuerda incompleta. Si aún se adivina el paso: barrida.
            if rel_interior < 0.016 and rel_l < 3.6:
                tipo, puntaje = "danada", max(hueco, 0.8)
            elif rel_interior < 0.016:
                tipo, puntaje = "incompleta", max(hueco, 0.88)
            else:
                tipo, puntaje = "barrida", max(plano, 0.84)
        else:
            opciones = {
                "barrida": plano if rel_h < altura_minima_rel * 1.4 else 0.0,
                "incompleta": hueco if rel_interior < 0.014 else hueco * 0.3,
                "mal_formada": paso_raro if rel_interior >= altura_minima_rel else paso_raro * 0.35,
                "danada": forma_rara if rel_l < 1.45 else forma_rara * 0.5,
            }
            tipo = max(opciones, key=opciones.get)
            puntaje = float(opciones[tipo])
        muestras.append(
            {
                "largo": int(largo),
                "rel_l": round(float(rel_l), 2),
                "rel_h": round(float(rel_h), 3),
                "corr": round(float(corr), 2),
                "tipo": tipo,
                "puntaje": round(float(puntaje), 2),
            }
        )
        if puntaje > 0.2:
            tramos.append((izq, der, puntaje, tipo))

    if not tramos:
        return {
            "puntaje": 0.08,
            "tipo": "ninguno",
            "tramos": [],
            "rel": rel,
            "dientes": len(picos),
            "muestras": muestras,
        }

    peor = max(tramos, key=lambda t: t[2])
    return {
        "puntaje": float(peor[2]),
        "tipo": peor[3],
        "tramos": tramos,
        "rel": rel,
        "dientes": len(picos),
        "muestras": muestras,
    }


def _preparar(bgr: np.ndarray) -> np.ndarray:
    alto, ancho = bgr.shape[:2]
    lado = max(alto, ancho)
    if lado > 1600:
        factor = 1600 / lado
        bgr = cv2.resize(bgr, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    elif lado < 640:
        bgr = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return bgr


def _confianza(puntaje: float, umbral: float) -> float:
    distancia = abs(puntaje - umbral)
    base = 1.0 / (1.0 + np.exp(-9.0 * (distancia - 0.06)))
    return float(np.clip(0.56 + 0.40 * base, 0.56, 0.96))


_TEXTO = {
    "ok": "La cuerda se ve pareja: el paso y la altura de los dientes se mantienen a lo largo del tornillo.",
    "barrida": "La cresta está aplastada en el tramo marcado. Esa parte de la cuerda se ve barrida.",
    "incompleta": "En el tramo marcado falta cuerda: el perfil se ve liso, sin dientes.",
    "danada": "Hay dientes mordidos o irregulares en la zona marcada.",
    "mal_formada": "El paso de la cuerda cambia de golpe en el tramo marcado; no está bien formada.",
    "no_detectado": "No encontré un tornillo claro. Usa un fondo liso que contraste y toma la foto de lado, con toda la cuerda a la vista.",
    "de_frente": "Esto no parece un tornillo de lado. Acércalo y tómalo de perfil para que se vea la cuerda.",
}


def analizar(imagen: np.ndarray, umbral: float | None = None, ya_preparada: bool = False) -> Resultado:
    config = cargar_configuracion()
    if umbral is None:
        umbral = float(config.get("umbral", PRIORS["umbral"]))
    altura_minima = float(config.get("altura_minima_rel", PRIORS["altura_minima_rel"]))
    if not ya_preparada:
        imagen = _preparar(imagen)
    alto, ancho = imagen.shape[:2]
    vacio = Resultado(
        veredicto="NO_DETECTADO",
        confianza=0.0,
        puntaje=0.0,
        tipo="no_detectado",
        explicacion=_TEXTO["no_detectado"],
        zonas=[],
        contorno=[],
        ancho=ancho,
        alto=alto,
    )

    mask = _mascara(imagen)
    if mask is None:
        return vacio
    perfil = _perfil(mask)
    if perfil is None:
        return vacio
    region = _region_de_cuerda(perfil["grosor"])
    if region is None:
        vacio.explicacion = _TEXTO["de_frente"]
        vacio.tipo = "de_frente"
        return vacio
    a, b = region
    grosor = perfil["grosor"][a:b]
    diametro = float(np.median(grosor))
    sup = perfil["superior"][a:b]
    inf = perfil["inferior"][a:b]
    # Paso aproximado para poder separar la onda lenta (cabeza, punta) de los dientes.
    sigma_lento = max(24.0, len(sup) / 5.0)
    bosquejo = sup - _suavizar(sup, sigma_lento)
    paso = _estimar_paso(bosquejo) or _estimar_paso(inf - _suavizar(inf, sigma_lento))
    if paso is None or paso < 6:
        pp = float(np.percentile(bosquejo, 98) - np.percentile(bosquejo, 2))
        if pp / (diametro + 1e-6) < altura_minima:
            contorno = _poligono(perfil, 0, len(perfil["grosor"]), pad=2.0)
            return Resultado(
                veredicto="DEFECTUOSO",
                confianza=_confianza(0.93, umbral),
                puntaje=0.93,
                tipo="barrida",
                explicacion=_TEXTO["barrida"],
                zonas=[_poligono(perfil, a, b)],
                contorno=contorno,
                ancho=ancho,
                alto=alto,
                detalle={"paso_px": 0, "dientes": 0, "diametro_px": round(diametro, 1), "umbral": umbral},
            )
        vacio.explicacion = _TEXTO["de_frente"]
        vacio.tipo = "de_frente"
        return vacio

    onda_sup = _suavizar(_suavizar(sup, paso * 2.3) - sup, 1.15)
    onda_inf = _suavizar(inf - _suavizar(inf, paso * 2.3), 1.15)
    # El paso definitivo sale del borde donde la cuerda se lee con más fuerza.
    paso_sup = _estimar_paso(onda_sup) or paso
    paso_inf = _estimar_paso(onda_inf) or paso
    fuerza_sup = float(np.std(onda_sup))
    fuerza_inf = float(np.std(onda_inf))
    paso = paso_sup if fuerza_sup >= fuerza_inf else paso_inf

    info_sup = _analizar_borde(onda_sup, paso, diametro, altura_minima)
    info_inf = _analizar_borde(onda_inf, paso, diametro, altura_minima)
    info = info_sup if info_sup["puntaje"] >= info_inf["puntaje"] else info_inf
    puntaje = float(info["puntaje"])
    tipo = info["tipo"] if puntaje >= umbral else "ninguno"
    veredicto = "DEFECTUOSO" if puntaje >= umbral else "OK"

    zonas = []
    if veredicto == "DEFECTUOSO":
        for origen in (info_sup, info_inf):
            for izq, der, puntaje_tramo, _tipo in origen["tramos"]:
                if puntaje_tramo < umbral:
                    continue
                zonas.append(_poligono(perfil, a + izq, a + der))
        if not zonas:
            zonas.append(_poligono(perfil, a, b))
        zonas = _unir_zonas(zonas, perfil)

    contorno = _poligono(perfil, 0, len(perfil["grosor"]), pad=2.0)
    explicacion = _TEXTO["ok"] if veredicto == "OK" else _TEXTO.get(tipo, _TEXTO["danada"])
    dientes = int(max(info_sup["dientes"], info_inf["dientes"]))
    return Resultado(
        veredicto=veredicto,
        confianza=_confianza(puntaje, umbral),
        puntaje=puntaje,
        tipo=tipo if veredicto == "DEFECTUOSO" else "ninguno",
        explicacion=explicacion,
        zonas=zonas,
        contorno=contorno,
        ancho=ancho,
        alto=alto,
        detalle={
            "paso_px": int(paso),
            "dientes": dientes,
            "diametro_px": round(diametro, 1),
            "amplitud_superior": round(float(info_sup["rel"]), 4),
            "amplitud_inferior": round(float(info_inf["rel"]), 4),
            "umbral": umbral,
            "origen_umbral": "calibracion" if (directorio_datos() / "calibracion.json").exists() else "fabrica",
        },
    )


def _unir_zonas(zonas: list, perfil: dict) -> list:
    """Une cajas que se pisan para no pintar el mismo tramo dos veces."""
    if len(zonas) <= 1:
        return zonas
    # Volvemos a los bins por la coordenada u del primer y segundo punto.
    intervalos = []
    eje = perfil["eje"]
    media = perfil["media"]
    u_min = perfil["u_min"]
    for zona in zonas:
        us = [float(np.dot(np.array(p) - media, eje)) for p in zona]
        b0 = int(np.floor(min(us) - u_min))
        b1 = int(np.ceil(max(us) - u_min))
        intervalos.append([b0, b1])
    intervalos.sort()
    unidos = [intervalos[0]]
    for b0, b1 in intervalos[1:]:
        if b0 <= unidos[-1][1] + 4:
            unidos[-1][1] = max(unidos[-1][1], b1)
        else:
            unidos.append([b0, b1])
    return [_poligono(perfil, b0, b1) for b0, b1 in unidos]


def inspeccionar(imagen: np.ndarray, umbral: float | None = None) -> Resultado:
    return analizar(imagen, umbral=umbral)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Uso: python -m rosca.detector foto.jpg")
        raise SystemExit(1)
    from rosca.imagenes import cargar

    resultado = analizar(cargar(Path(sys.argv[1])))
    print(f"{resultado.veredicto}  confianza {resultado.confianza:.0%}  {resultado.tipo}")
    print(resultado.explicacion)
