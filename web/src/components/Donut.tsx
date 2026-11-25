type Props = {
  ok: number
  defectuosos: number
}

export function Donut({ ok, defectuosos }: Props) {
  const total = ok + defectuosos
  const radio = 52
  const circunferencia = 2 * Math.PI * radio
  const largoOk = total ? (ok / total) * circunferencia : 0
  const largoMal = total ? (defectuosos / total) * circunferencia : 0

  return (
    <svg viewBox="0 0 140 140" className="h-36 w-36 shrink-0" role="img" aria-label={`${total} tornillos revisados`}>
      <circle cx="70" cy="70" r={radio} fill="none" stroke="#e7dfd2" strokeWidth="14" />
      {total > 0 && (
        <>
          <circle
            cx="70"
            cy="70"
            r={radio}
            fill="none"
            stroke="#0d7a45"
            strokeWidth="14"
            strokeDasharray={`${largoOk} ${circunferencia - largoOk}`}
            transform="rotate(-90 70 70)"
          />
          <circle
            cx="70"
            cy="70"
            r={radio}
            fill="none"
            stroke="#d61f3a"
            strokeWidth="14"
            strokeDasharray={`${largoMal} ${circunferencia - largoMal}`}
            strokeDashoffset={-largoOk}
            transform="rotate(-90 70 70)"
          />
        </>
      )}
      <text x="70" y="68" textAnchor="middle" fill="#1c1612" fontFamily="Fraunces, Georgia, serif" fontSize="30">
        {total}
      </text>
      <text x="70" y="88" textAnchor="middle" fill="#5c5148" fontFamily="Outfit, sans-serif" fontSize="11">
        revisados
      </text>
    </svg>
  )
}
