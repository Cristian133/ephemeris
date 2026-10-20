import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import HorasDeSol from './pages/HorasDeSol'
import Trayectoria from './pages/Trayectoria'
import Mediodia from './pages/Mediodia'
import Irradiancia from './pages/Irradiancia'
import Crepusculos from './pages/Crepusculos'
import Estaciones from './pages/Estaciones'
import PanelSolar from './pages/PanelSolar'
import Luna from './pages/Luna'
import Eclipses from './pages/Eclipses'
import Mareas from './pages/Mareas'
import Pascua from './pages/Pascua'
import Lluvia from './pages/Lluvia'
import Nubosidad from './pages/Nubosidad'
import SolReal from './pages/SolReal'
import RadiacionReal from './pages/RadiacionReal'

/** Una ruta por feature del plan técnico (sección 5): horas de sol
 * (puntos 1+2), trayectoria (punto 3), mediodía (punto 4), irradiancia
 * (punto 5), más crepúsculos, estaciones y panel solar, y los de la
 * etapa 2: Luna, eclipses, mareas teóricas y Pascua. `Layout` comparte
 * la navegación, la ubicación y la fecha. La etapa 3 (meteorología)
 * son la lluvia, la nubosidad, el sol real y la radiación real. */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HorasDeSol />} />
        <Route path="trayectoria" element={<Trayectoria />} />
        <Route path="mediodia" element={<Mediodia />} />
        <Route path="irradiancia" element={<Irradiancia />} />
        <Route path="crepusculos" element={<Crepusculos />} />
        <Route path="estaciones" element={<Estaciones />} />
        <Route path="panel" element={<PanelSolar />} />
        <Route path="luna" element={<Luna />} />
        <Route path="eclipses" element={<Eclipses />} />
        <Route path="mareas" element={<Mareas />} />
        <Route path="pascua" element={<Pascua />} />
        <Route path="lluvia" element={<Lluvia />} />
        <Route path="nubosidad" element={<Nubosidad />} />
        <Route path="sol-real" element={<SolReal />} />
        <Route path="radiacion-real" element={<RadiacionReal />} />
      </Route>
    </Routes>
  )
}
