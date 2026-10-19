const COMPASS_POINTS = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']

/** Punto cardinal/intercardinal (8 rumbos) más cercano a un azimut dado
 * (0°=Norte, sentido horario). */
export function compassLabel(azimuthDeg: number): string {
  // Doble modulo: un azimut negativo (ej. -90) o > 360 no debe indexar fuera.
  const index = (((Math.round(azimuthDeg / 45) % 8) + 8) % 8)
  return COMPASS_POINTS[index]
}
