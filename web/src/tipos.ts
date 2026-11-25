export type Punto = [number, number]

export type Resultado = {
  veredicto: "OK" | "DEFECTUOSO" | "NO_DETECTADO"
  confianza: number
  puntaje: number
  tipo: string
  explicacion: string
  zonas: Punto[][]
  contorno: Punto[]
  ancho: number
  alto: number
  detalle: {
    paso_px?: number
    dientes?: number
    diametro_px?: number
    umbral?: number
    origen_umbral?: string
  }
  imagen_jpeg: string
  id_historial: number | null
}

export type Ejemplo = {
  id: string
  titulo: string
  url: string
}

export type ItemHistorial = {
  id: number
  fecha: string
  veredicto: "OK" | "DEFECTUOSO"
  confianza: number
  puntaje: number
  tipo: string
  explicacion: string
  origen: string
  nombre: string
}

export type Resumen = {
  total: number
  ok: number
  defectuosos: number
  porcentaje_ok: number
  porcentaje_defectuosos: number
}

export type Calibracion = {
  umbral: number
  origen: "fabrica" | "propia"
  n_buenos: number
  n_defectuosos: number
  creado: string | null
  metodo: string
}

export const NOMBRE_TIPO: Record<string, string> = {
  ninguno: "Cuerda pareja",
  barrida: "Cuerda barrida",
  incompleta: "Cuerda incompleta",
  danada: "Cuerda dañada",
  mal_formada: "Cuerda mal formada",
  no_detectado: "Sin lectura",
  de_frente: "Ángulo incorrecto",
}

export const NOMBRE_ORIGEN: Record<string, string> = {
  subida: "Foto",
  camara: "Cámara",
  ejemplo: "Ejemplo",
}
