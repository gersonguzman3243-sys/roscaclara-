import { useEffect, useRef, useState } from "react"
import { Button } from "./ui/button.tsx"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog.tsx"

type Props = {
  abierto: boolean
  onCerrar: (abierto: boolean) => void
  onCaptura: (archivo: File) => void
}

export function CamaraDialog({ abierto, onCerrar, onCaptura }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!abierto) return
    let flujo: MediaStream | null = null
    let cancelado = false
    setError(null)
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      .then((stream) => {
        if (cancelado) {
          stream.getTracks().forEach((pista) => pista.stop())
          return
        }
        flujo = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          void videoRef.current.play()
        }
      })
      .catch(() => {
        setError("No pude abrir la cámara. Revisa el permiso o sube una foto.")
      })
    return () => {
      cancelado = true
      flujo?.getTracks().forEach((pista) => pista.stop())
    }
  }, [abierto])

  function capturar() {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const lienzo = document.createElement("canvas")
    lienzo.width = video.videoWidth
    lienzo.height = video.videoHeight
    const contexto = lienzo.getContext("2d")
    if (!contexto) return
    contexto.drawImage(video, 0, 0)
    lienzo.toBlob(
      (blob) => {
        if (!blob) return
        const archivo = new File([blob], `camara-${Date.now()}.jpg`, { type: "image/jpeg" })
        onCaptura(archivo)
        onCerrar(false)
      },
      "image/jpeg",
      0.92,
    )
  }

  return (
    <Dialog open={abierto} onOpenChange={onCerrar}>
      <DialogContent className="max-w-xl">
        <DialogTitle>Tomar foto</DialogTitle>
        <DialogDescription>Pon el tornillo de lado, con la cuerda a la vista y un fondo que contraste.</DialogDescription>
        <div className="mt-4 overflow-hidden rounded-2xl bg-ink">
          {error ? (
            <p className="px-4 py-16 text-center text-sm text-cream">{error}</p>
          ) : (
            <video ref={videoRef} className="aspect-video w-full object-cover" autoPlay playsInline muted />
          )}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </Button>
          <Button onClick={capturar} disabled={Boolean(error)}>
            Usar esta foto
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
