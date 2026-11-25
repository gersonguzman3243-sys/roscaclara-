import type { Calibracion, Ejemplo, ItemHistorial, Resumen, Resultado } from "./tipos.ts"

async function mensajeError(respuesta: Response, respaldo: string) {
  const cuerpo = await respuesta.json().catch(() => null)
  if (cuerpo && typeof cuerpo.detail === "string") return cuerpo.detail
  return respaldo
}

export async function obtenerEjemplos(): Promise<Ejemplo[]> {
  const respuesta = await fetch("/api/ejemplos")
  if (!respuesta.ok) throw new Error("No pude cargar los ejemplos.")
  const cuerpo = (await respuesta.json()) as { ejemplos: Ejemplo[] }
  return cuerpo.ejemplos
}

export async function inspeccionar(archivo: Blob, nombre: string, origen: string): Promise<Resultado> {
  const datos = new FormData()
  datos.append("archivo", archivo, nombre)
  datos.append("nombre", nombre)
  datos.append("origen", origen)
  const respuesta = await fetch("/api/inspeccionar", { method: "POST", body: datos })
  if (!respuesta.ok) {
    throw new Error(await mensajeError(respuesta, "No pude revisar esa imagen."))
  }
  return respuesta.json() as Promise<Resultado>
}

export async function obtenerHistorial(): Promise<{ resumen: Resumen; items: ItemHistorial[] }> {
  const respuesta = await fetch("/api/historial")
  if (!respuesta.ok) throw new Error("No pude leer el historial.")
  return respuesta.json() as Promise<{ resumen: Resumen; items: ItemHistorial[] }>
}

export async function vaciarHistorial() {
  const respuesta = await fetch("/api/historial", { method: "DELETE" })
  if (!respuesta.ok) throw new Error("No pude vaciar el historial.")
}

export async function obtenerCalibracion(): Promise<Calibracion> {
  const respuesta = await fetch("/api/calibracion")
  if (!respuesta.ok) throw new Error("No pude leer la calibración.")
  return respuesta.json() as Promise<Calibracion>
}

export async function recalibrar(): Promise<Calibracion> {
  const respuesta = await fetch("/api/calibrar", { method: "POST" })
  if (!respuesta.ok) {
    throw new Error(await mensajeError(respuesta, "No pude recalibrar."))
  }
  return respuesta.json() as Promise<Calibracion>
}
