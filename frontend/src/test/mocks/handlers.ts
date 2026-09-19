import type { HttpHandler } from 'msw'

// Shared/default MSW request handlers, if any are ever needed across
// multiple test files. Empty for now — individual test files register
// their own handlers per-test via `server.use(...)` (see
// frontend/src/test/mocks/server.ts).
export const handlers: HttpHandler[] = []
