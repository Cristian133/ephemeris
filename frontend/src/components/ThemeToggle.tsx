import { useTheme } from '../context/ThemeContext'
import { THEME_OPTIONS } from '../utils/theme'

/** Selector de tema: claro, oscuro o el del sistema operativo. */
export function ThemeToggle() {
  const { preference, resolved, setPreference } = useTheme()

  return (
    <div
      role="group"
      aria-label="Tema"
      style={{
        display: 'inline-flex',
        border: '1px solid var(--axis)',
        borderRadius: '0.375rem',
        overflow: 'hidden',
      }}
    >
      {THEME_OPTIONS.map((option) => {
        const active = preference === option.value
        const title =
          option.value === 'system'
            ? `Seguir el tema del sistema (ahora ${resolved === 'dark' ? 'oscuro' : 'claro'})`
            : `Tema ${option.label.toLowerCase()}`
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            aria-label={option.label}
            title={title}
            onClick={() => setPreference(option.value)}
            style={{
              padding: '0.4rem 0.55rem',
              border: 'none',
              background: active ? 'var(--series-1)' : 'var(--surface-1)',
              color: active ? '#fff' : 'var(--text-primary)',
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            <span aria-hidden="true">{option.icon}</span>
          </button>
        )
      })}
    </div>
  )
}
