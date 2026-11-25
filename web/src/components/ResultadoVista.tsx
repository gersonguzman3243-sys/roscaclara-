import { NOMBRE_TIPO, type Resultado } from "../tipos.ts"
import { porcentaje } from "../lib/utils.ts"

type Props = {
  resultado: Resultado | null
  cargando: boolean
}

function trazo(puntos: [number, number][]) {
  return puntos.map(([x, y]) => `${x},${y}`).join(" ")
}

export function ResultadoVista({ resultado, cargando }: Props) {
  if (cargando && !resultado) {
    return <Cargando />
  }
  if (!resultado) {
    return (
      <div className="flex min-h-[280px] flex-col justify-center rounded-[28px] border border-dashed border-ink/15 bg-cream/70 px-8 py-10">
        <p className="font-display text-3xl text-ink">Aquí cae el veredicto.</p>
        <p className="mt-3 max-w-md text-ink-soft">
          Elige un ejemplo o suelta una foto. Vas a ver el tornillo, la zona marcada y si la cuerda va o no va.
        </p>
      </div>
    )
  }

  const ok = resultado.veredicto === "OK"
  const fallo = resultado.veredicto === "DEFECTUOSO"
  const confianza = porcentaje(resultado.confianza)

  return (
    <div className={`surgir grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.9fr)] ${cargando ? "opacity-70" : ""}`}>
      <figure className="overflow-hidden rounded-[28px] bg-[#d5d5d5] shadow-card">
        <div className="relative" style={{ aspectRatio: `${resultado.ancho} / ${resultado.alto}` }}>
          <img
            src={`data:image/jpeg;base64,${resultado.imagen_jpeg}`}
            alt="Tornillo revisado"
            className="absolute inset-0 h-full w-full object-cover"
          />
          <svg
            viewBox={`0 0 ${resultado.ancho} ${resultado.alto}`}
            className="absolute inset-0 h-full w-full"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {resultado.contorno.length > 0 && (
              <polygon
                points={trazo(resultado.contorno)}
                fill="none"
                stroke={ok ? "#1f9d5c" : "#fffaf3"}
                strokeWidth={Math.max(3, resultado.ancho / 220)}
              />
            )}
            {resultado.zonas.map((zona, indice) => (
              <polygon
                key={indice}
                points={trazo(zona)}
                fill="rgba(214,31,58,0.38)"
                stroke="#d61f3a"
                strokeWidth={Math.max(3, resultado.ancho / 180)}
              />
            ))}
          </svg>
          {cargando && (
            <div className="absolute inset-x-0 bottom-0 h-1 overflow-hidden bg-white/20">
              <div className="h-full w-1/3 bg-copper" style={{ animation: "barra 1s linear infinite" }} />
            </div>
          )}
        </div>
      </figure>

      <div
        role="status"
        className={`sello flex flex-col justify-between overflow-hidden rounded-[28px] p-6 shadow-stamp sm:p-8 ${
          ok ? "bg-ok-soft" : fallo ? "bg-defect-soft" : "bg-cream"
        }`}
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-soft">Veredicto</p>
          <p
            className={`mt-2 font-display text-4xl leading-[0.95] tracking-tight sm:text-5xl ${
              ok ? "text-ok" : fallo ? "text-defect" : "text-ink"
            }`}
          >
            {resultado.veredicto === "NO_DETECTADO" ? "Sin lectura" : resultado.veredicto}
          </p>
          <p className="mt-4 text-lg font-medium text-ink">{NOMBRE_TIPO[resultado.tipo] ?? "Revisión"}</p>
          <p className="mt-2 text-sm leading-relaxed text-ink-soft">{resultado.explicacion}</p>
        </div>
        {resultado.veredicto !== "NO_DETECTADO" && (
          <div className="mt-6">
            <div className="mb-2 flex items-baseline justify-between text-sm">
              <span className="font-medium text-ink">Confianza {confianza}</span>
              <span className="text-ink-soft">respecto al umbral</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ink/10">
              <div
                className={`h-full rounded-full ${ok ? "bg-ok" : "bg-defect"}`}
                style={{ width: confianza }}
              />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink-soft">
              {resultado.detalle.dientes
                ? `Se leyeron ${resultado.detalle.dientes} dientes`
                : "No se distinguieron dientes"}
              {resultado.detalle.paso_px ? ` · paso de ${resultado.detalle.paso_px} px` : ""}. La confianza dice qué tan
              lejos quedó del corte, no una probabilidad medida en taller.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function Cargando() {
  return (
    <div className="flex min-h-[280px] items-center justify-center rounded-[28px] bg-cream shadow-card">
      <div className="text-center">
        <div className="mx-auto mb-4 h-1.5 w-40 overflow-hidden rounded-full bg-ink/10">
          <div className="h-full w-1/2 bg-copper" style={{ animation: "barra 1s linear infinite" }} />
        </div>
        <p className="font-display text-2xl">Revisando la cuerda…</p>
      </div>
    </div>
  )
}
