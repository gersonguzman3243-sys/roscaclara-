import { Camera, Upload } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  inspeccionar,
  obtenerCalibracion,
  obtenerEjemplos,
  obtenerHistorial,
  recalibrar,
  vaciarHistorial,
} from "./api.ts"
import { CamaraDialog } from "./components/CamaraDialog.tsx"
import { HistorialPanel } from "./components/HistorialPanel.tsx"
import { ResultadoVista } from "./components/ResultadoVista.tsx"
import { Button } from "./components/ui/button.tsx"
import type { Calibracion, Ejemplo, ItemHistorial, Resumen, Resultado } from "./tipos.ts"

const resumenVacio: Resumen = {
  total: 0,
  ok: 0,
  defectuosos: 0,
  porcentaje_ok: 0,
  porcentaje_defectuosos: 0,
}

export default function App() {
  const archivoRef = useRef<HTMLInputElement>(null)
  const [ejemplos, setEjemplos] = useState<Ejemplo[]>([])
  const [ejemploActivo, setEjemploActivo] = useState<string | null>(null)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [camaraAbierta, setCamaraAbierta] = useState(false)
  const [items, setItems] = useState<ItemHistorial[]>([])
  const [resumen, setResumen] = useState<Resumen>(resumenVacio)
  const [calibracion, setCalibracion] = useState<Calibracion | null>(null)
  const [calibrando, setCalibrando] = useState(false)
  const [avisoCalibracion, setAvisoCalibracion] = useState<string | null>(null)
  const arrastres = useRef(0)

  const refrescarHistorial = useCallback(async () => {
    const datos = await obtenerHistorial()
    setItems(datos.items)
    setResumen(datos.resumen)
  }, [])

  useEffect(() => {
    void obtenerEjemplos().then(setEjemplos).catch(() => setError("No pude cargar los ejemplos."))
    void refrescarHistorial().catch(() => undefined)
    void obtenerCalibracion().then(setCalibracion).catch(() => undefined)
  }, [refrescarHistorial])

  const revisar = useCallback(
    async (archivo: Blob, nombre: string, origen: string) => {
      setCargando(true)
      setError(null)
      try {
        const nuevo = await inspeccionar(archivo, nombre, origen)
        setResultado(nuevo)
        if (nuevo.id_historial) await refrescarHistorial()
        document.getElementById("veredicto")?.scrollIntoView({ behavior: "smooth", block: "start" })
      } catch (causa) {
        setError(causa instanceof Error ? causa.message : "No pude revisar esa imagen.")
      } finally {
        setCargando(false)
      }
    },
    [refrescarHistorial],
  )

  useEffect(() => {
    function alEntrar(evento: DragEvent) {
      if (!evento.dataTransfer?.types.includes("Files")) return
      evento.preventDefault()
      arrastres.current += 1
      setArrastrando(true)
    }
    function alSalir(evento: DragEvent) {
      if (!evento.dataTransfer?.types.includes("Files")) return
      arrastres.current = Math.max(0, arrastres.current - 1)
      if (arrastres.current === 0) setArrastrando(false)
    }
    function alSoltar(evento: DragEvent) {
      if (!evento.dataTransfer?.types.includes("Files")) return
      evento.preventDefault()
      arrastres.current = 0
      setArrastrando(false)
      const archivo = evento.dataTransfer.files[0]
      if (archivo) {
        setEjemploActivo(null)
        void revisar(archivo, archivo.name, "subida")
      }
    }
    function alPasar(evento: DragEvent) {
      if (evento.dataTransfer?.types.includes("Files")) evento.preventDefault()
    }
    function alPegar(evento: ClipboardEvent) {
      const archivo = [...(evento.clipboardData?.files ?? [])].find((item) => item.type.startsWith("image/"))
      if (!archivo) return
      setEjemploActivo(null)
      void revisar(archivo, archivo.name || "pegada.jpg", "subida")
    }
    window.addEventListener("dragenter", alEntrar)
    window.addEventListener("dragleave", alSalir)
    window.addEventListener("dragover", alPasar)
    window.addEventListener("drop", alSoltar)
    window.addEventListener("paste", alPegar)
    return () => {
      window.removeEventListener("dragenter", alEntrar)
      window.removeEventListener("dragleave", alSalir)
      window.removeEventListener("dragover", alPasar)
      window.removeEventListener("drop", alSoltar)
      window.removeEventListener("paste", alPegar)
    }
  }, [revisar])

  async function probarEjemplo(ejemplo: Ejemplo) {
    setEjemploActivo(ejemplo.id)
    const respuesta = await fetch(ejemplo.url)
    if (!respuesta.ok) {
      setError("No pude abrir ese ejemplo.")
      return
    }
    const blob = await respuesta.blob()
    await revisar(blob, ejemplo.titulo, "ejemplo")
  }

  async function calibrarAhora() {
    setCalibrando(true)
    setAvisoCalibracion(null)
    try {
      const nueva = await recalibrar()
      setCalibracion(nueva)
      setAvisoCalibracion(nueva.metodo)
    } catch (causa) {
      setAvisoCalibracion(causa instanceof Error ? causa.message : "No pude recalibrar.")
    } finally {
      setCalibrando(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 pt-5 sm:px-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <a href="#inicio" className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-ink" aria-hidden="true">
            <svg viewBox="0 0 32 32" className="h-7 w-7">
              <path d="M6 14.2h5v3.6H6z" fill="#c4622d" />
              <path d="M11 12.6h2.4v6.8H11z" fill="#c4622d" />
              <path
                d="M14 16.2c.9-1.5 1.8-1.5 2.6 0s1.7 1.5 2.6 0 1.7-1.5 2.5 0 1.5 1.3 2.3 0"
                fill="none"
                stroke="#fffaf3"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path d="M24 16.8 27.2 16" stroke="#fffaf3" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </span>
          <span>
            <span className="block font-display text-2xl leading-none">RoscaClara</span>
            <span className="text-sm text-ink-soft">Inspección de cuerda</span>
          </span>
        </a>
        <a href="#historial" className="text-sm font-semibold text-ink-soft hover:text-ink">
          Historial{resumen.total > 0 ? ` · ${resumen.total}` : ""}
        </a>
      </header>

      <section id="inicio" className="overflow-hidden rounded-[32px] bg-ink text-cream shadow-card">
        <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[0.9fr_1.1fr] lg:p-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-copper">Paso 1</p>
            <h1 className="mt-3 font-display text-4xl leading-[1.05] sm:text-5xl">¿La cuerda todavía sirve?</h1>
            <p className="mt-4 max-w-md text-base leading-relaxed text-cream/75">
              Sube una foto, usa la cámara o prueba un ejemplo. Marcamos el tramo dañado y te decimos si va o no va.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button variant="default" size="lg" onClick={() => document.getElementById("ejemplos")?.scrollIntoView({ behavior: "smooth" })}>
                Probar con ejemplos
              </Button>
              <Button variant="cream" size="lg" onClick={() => archivoRef.current?.click()}>
                <Upload className="h-4 w-4" />
                Subir foto
              </Button>
              <Button variant="ghostLight" size="lg" onClick={() => setCamaraAbierta(true)}>
                <Camera className="h-4 w-4" />
                Cámara
              </Button>
            </div>
            <p className="mt-4 text-sm text-cream/55">También puedes arrastrar la foto a cualquier parte, o pegarla con Ctrl+V.</p>
            <input
              ref={archivoRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(evento) => {
                const archivo = evento.target.files?.[0]
                evento.target.value = ""
                if (!archivo) return
                setEjemploActivo(null)
                void revisar(archivo, archivo.name, "subida")
              }}
            />
          </div>

          <div id="ejemplos">
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="font-display text-2xl">Ejemplos listos</h2>
              <p className="text-sm text-cream/60">Sin fotos propias</p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {ejemplos.map((ejemplo) => {
                const activo = ejemploActivo === ejemplo.id
                return (
                  <button
                    key={ejemplo.id}
                    type="button"
                    onClick={() => void probarEjemplo(ejemplo)}
                    className={`group overflow-hidden rounded-2xl bg-white/5 text-left ring-2 transition duration-200 hover:-translate-y-0.5 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-copper ${
                      activo ? "ring-copper" : "ring-transparent"
                    }`}
                  >
                    <img src={ejemplo.url} alt="" className="aspect-[5/3] w-full object-cover" />
                    <span className="block px-2.5 py-2 text-sm font-medium">{ejemplo.titulo}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {error && (
        <p className="mt-4 rounded-2xl bg-defect-soft px-4 py-3 text-sm text-defect" role="alert">
          {error}
        </p>
      )}

      <section id="veredicto" className="mt-8 scroll-mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-copper">Paso 2</p>
        <h2 className="mb-4 font-display text-4xl">El veredicto</h2>
        <ResultadoVista resultado={resultado} cargando={cargando} />
      </section>

      <HistorialPanel
        resumen={resumen}
        items={items}
        onVaciar={async () => {
          await vaciarHistorial()
          await refrescarHistorial()
        }}
      />

      <section className="mt-14 grid gap-4 lg:grid-cols-2">
        <div className="rounded-[28px] bg-cream p-6 shadow-card">
          <h2 className="font-display text-2xl">Para que la foto sirva</h2>
          <ul className="mt-4 space-y-2 text-sm leading-relaxed text-ink-soft">
            <li>De lado, con toda la cuerda a la vista. No de frente, por la punta.</li>
            <li>Fondo liso que contraste: claro si el tornillo es oscuro, u oscuro si brilla.</li>
            <li>Luz pareja. Un reflejo fuerte sobre la cresta se lee como un diente comido.</li>
            <li>Un tornillo por foto, y que ocupe buena parte del cuadro.</li>
          </ul>
        </div>
        <div className="rounded-[28px] bg-cream p-6 shadow-card">
          <h2 className="font-display text-2xl">Cuando tengas tus fotos</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-soft">
            Guarda tornillos buenos en <span className="font-semibold text-ink">datos/buenos</span> y, si tienes,
            defectuosos en <span className="font-semibold text-ink">datos/defectuosos</span>. Luego recalibra. Mínimo 5
            buenos; lo útil es 30 o más, con la misma luz.
          </p>
          <p className="mt-3 text-sm text-ink-soft">
            {calibracion?.origen === "propia"
              ? `Umbral propio: ${calibracion.umbral}. ${calibracion.metodo}`
              : "Hoy usa el umbral de fábrica, afinado solo con los ejemplos."}
          </p>
          {avisoCalibracion && <p className="mt-3 text-sm font-medium text-ink">{avisoCalibracion}</p>}
          <Button className="mt-4" onClick={() => void calibrarAhora()} disabled={calibrando}>
            {calibrando ? "Recalibrando…" : "Recalibrar ahora"}
          </Button>
        </div>
      </section>

      {arrastrando && (
        <div className="pointer-events-none fixed inset-4 z-40 grid place-items-center rounded-[32px] border-2 border-dashed border-copper bg-cream/85 text-center">
          <p className="font-display text-4xl text-ink">Suelta la foto del tornillo</p>
        </div>
      )}

      <CamaraDialog
        abierto={camaraAbierta}
        onCerrar={setCamaraAbierta}
        onCaptura={(archivo) => {
          setEjemploActivo(null)
          void revisar(archivo, archivo.name, "camara")
        }}
      />
    </div>
  )
}
