import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Separate config, not merged into vitest.config.ts's `test.include`,
// so `npm test` (CI) never runs timing-sensitive assertions -- a slow
// CI runner shouldn't be able to fail the correctness suite. Run these
// explicitly with `npm run test:perf`.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    include: ['**/*.bench.test.tsx'],
  },
})
