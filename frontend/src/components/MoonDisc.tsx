const SIZE = 120
const RADIUS = 50
const CENTER = SIZE / 2

/** Disco de la Luna con su parte iluminada.
 *
 * La región iluminada es una media circunferencia (el limbo) más una
 * semielipse (el terminador) de semieje horizontal `RADIUS * |2f - 1|`, con
 * `f` la fracción iluminada. Con la Luna creciente vista desde el hemisferio
 * norte la luz está a la derecha; menguante, a la izquierda; y desde el
 * hemisferio sur todo se invierte (se ve "boca abajo"). */
export function MoonDisc({
  fraction,
  waxing,
  southern,
}: {
  fraction: number
  waxing: boolean
  southern: boolean
}) {
  const clamped = Math.max(0, Math.min(1, fraction))
  const terminatorRx = RADIUS * Math.abs(2 * clamped - 1)
  // Terminador: convexo hacia el lado oscuro si la fase es gibosa (f > 0.5),
  // hacia el lado iluminado si es creciente o menguante (f < 0.5).
  const terminatorSweep = clamped > 0.5 ? 1 : 0
  const top = CENTER - RADIUS
  const bottom = CENTER + RADIUS
  const lit =
    `M ${CENTER} ${top} A ${RADIUS} ${RADIUS} 0 0 1 ${CENTER} ${bottom} ` +
    `A ${terminatorRx} ${RADIUS} 0 0 ${terminatorSweep} ${CENTER} ${top} Z`
  const mirrored = waxing === southern // luz a la izquierda
  const percent = Math.round(clamped * 100)

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`Luna iluminada al ${percent}%`}
    >
      <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="var(--surface-2, #2b3340)" stroke="var(--axis)" />
      {clamped > 0.005 && (
        <path
          d={lit}
          fill="var(--moon-lit, #f4ecc8)"
          transform={mirrored ? `translate(${SIZE} 0) scale(-1 1)` : undefined}
        />
      )}
      <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="none" stroke="var(--axis)" />
    </svg>
  )
}
