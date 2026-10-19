import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Las paginas cargan datos con el patron fetch-en-effect (resetear
      // error/estado al cambiar las dependencias y luego pedir a la API).
      // La regla nueva de react-hooks v7 lo marca, pero migrarlo a una
      // libreria de datos queda fuera de alcance y el patron es correcto
      // (las carreras se evitan con `cancelled`/AbortController).
      'react-hooks/set-state-in-effect': 'off',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  {
    // Un contexto exporta su Provider y su hook `useX` desde el mismo
    // archivo; separarlos no aporta nada y solo afecta el fast refresh.
    files: ['src/context/*.tsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
)
