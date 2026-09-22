import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    // Perf/benchmark tests (*.bench.test.tsx) are timing-sensitive and
    // don't belong gating the same `npm test` run as correctness tests --
    // see vitest.bench.config.ts, run via `npm run test:perf`.
    exclude: [...configDefaults.exclude, '**/*.bench.test.tsx'],
  },
})
