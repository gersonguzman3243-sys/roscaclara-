import { Download, Trash2 } from "lucide-react"
import { useState } from "react"
import { fechaLocal, porcentaje } from "../lib/utils.ts"
import { NOMBRE_ORIGEN, NOMBRE_TIPO, type ItemHistorial, type Resumen } from "../tipos.ts"
import { Donut } from "./Donut.tsx"
import { Button } from "./ui/button.tsx"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog.tsx"

type Filtro = "todos" | "OK" | "DEFECTUOSO"

type Props = {
  resumen: Resumen
  items: ItemHistorial[]
  onVaciar: () => Promise<void>
}

export function HistorialPanel({ resumen, items, onVaciar }: Props) {
  const [filtro, setFiltro] = useState<Filtro>("todos")
  const [confirmar, setConfirmar] = useState(false)
  const [limpiando, setLimpiando] = useState(false)
  const visibles = items.filter((item) => filtro === "todos" || item.veredicto === filtro)

  async function vaciar() {
    setLimpiando(true)
    try {
      await onVaciar()
      setConfirmar(false)
    } finally {
      setLimpiando(false)
    }
  }

  return (
    <section id="historial" className="mt-14">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-copper">Paso 3</p>
          <h2 className="font-display text-4xl">Historial del turno</h2>
          <p className="mt-1 text-ink-soft">Cada tornillo que revisas se anota solo, con su foto chica y la hora.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild={false} onClick={() => (window.location.href = "/api/historial.csv")}>
            <Download className="h-4 w-4" />
            Exportar CSV
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirmar(true)} disabled={resumen.total === 0}>
            <Trash2 className="h-4 w-4" />
            Vaciar historial
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[auto_1fr]">
        <div className="flex flex-col gap-4 rounded-[28px] bg-cream p-5 shadow-card sm:flex-row sm:items-center lg:flex-col lg:items-start">
          <Donut ok={resumen.ok} defectuosos={resumen.defectuosos} />
          <dl className="grid w-full grid-cols-2 gap-3 text-sm">
            <Stat etiqueta="OK" valor={String(resumen.ok)} tono="ok" />
            <Stat etiqueta="Defectuosos" valor={String(resumen.defectuosos)} tono="mal" />
            <Stat etiqueta="% OK" valor={`${resumen.porcentaje_ok}%`} />
            <Stat etiqueta="% defectuosos" valor={`${resumen.porcentaje_defectuosos}%`} />
          </dl>
        </div>

        <div className="rounded-[28px] bg-cream p-4 shadow-card sm:p-5">
          <div className="mb-4 flex flex-wrap gap-2">
            {(
              [
                ["todos", "Todos"],
                ["OK", "OK"],
                ["DEFECTUOSO", "Defectuosos"],
              ] as const
            ).map(([id, etiqueta]) => (
              <button
                key={id}
                type="button"
                onClick={() => setFiltro(id)}
                className={`rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                  filtro === id ? "bg-ink text-cream" : "bg-paper text-ink hover:bg-ink/5"
                }`}
              >
                {etiqueta}
              </button>
            ))}
          </div>

          {visibles.length === 0 ? (
            <p className="px-2 py-10 text-center text-ink-soft">
              {resumen.total === 0
                ? "Todavía no hay piezas. Revisa un tornillo —un ejemplo sirve— y aparecerá aquí."
                : "Nada con ese filtro."}
            </p>
          ) : (
            <ul className="divide-y divide-ink/10">
              {visibles.map((item) => {
                const ok = item.veredicto === "OK"
                return (
                  <li key={item.id} className="flex items-center gap-3 py-3">
                    <img
                      src={`/api/historial/${item.id}/miniatura`}
                      alt=""
                      className={`h-14 w-20 shrink-0 rounded-xl object-cover ring-2 sm:h-16 sm:w-24 ${ok ? "ring-ok" : "ring-defect"}`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{item.nombre}</p>
                      <p className="truncate text-sm text-ink-soft">
                        {fechaLocal(item.fecha)} · {NOMBRE_ORIGEN[item.origen] ?? item.origen} ·{" "}
                        {NOMBRE_TIPO[item.tipo] ?? item.tipo}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className={`font-display text-base leading-none sm:text-lg ${ok ? "text-ok" : "text-defect"}`}>
                        {item.veredicto}
                      </p>
                      <p className="mt-1 text-xs text-ink-soft">{porcentaje(item.confianza)}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>

      <Dialog open={confirmar} onOpenChange={setConfirmar}>
        <DialogContent>
          <DialogTitle>¿Vaciar el historial?</DialogTitle>
          <DialogDescription>
            Se borran todas las piezas anotadas en este equipo. No se puede deshacer.
          </DialogDescription>
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmar(false)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => void vaciar()} disabled={limpiando}>
              {limpiando ? "Borrando…" : "Sí, vaciar"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  )
}

function Stat({ etiqueta, valor, tono }: { etiqueta: string; valor: string; tono?: "ok" | "mal" }) {
  return (
    <div className="rounded-2xl bg-paper px-3 py-2">
      <dt className="text-xs text-ink-soft">{etiqueta}</dt>
      <dd className={`font-display text-2xl ${tono === "ok" ? "text-ok" : tono === "mal" ? "text-defect" : "text-ink"}`}>
        {valor}
      </dd>
    </div>
  )
}
