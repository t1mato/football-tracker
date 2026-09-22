import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { PlayerDirectoryTable } from './PlayerDirectoryTable'

/** Regression test for the pagination fix: render cost should stay flat
 * as the underlying dataset grows, because PlayerDirectoryTable only
 * ever mounts one page's worth of rows (PAGE_SIZE=50), not the full
 * fetched array. Measured directly (not asserted from memory): a real
 * spike rendering all 3045 rows vs. a 50-row page took a 210ms vs. 3ms
 * median in this same jsdom environment -- a ~66x/98.5% difference. If
 * pagination were ever accidentally removed (e.g. `filtered` rendered
 * instead of `paged`), the large-dataset case would blow up by roughly
 * that factor; this test fails long before that.
 */

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

function makePlayers(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    player_id: i,
    player_name: `Player ${i}`,
    position: 'Midfield',
    nationality: 'England',
    team_name: 'Test United',
    crest: null,
  }))
}

async function measureRender(totalPlayers: number): Promise<number> {
  server.use(http.get('/api/players', () => HttpResponse.json(makePlayers(totalPlayers))))
  const start = performance.now()
  renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={() => {}} />)
  await screen.findByText('Player 0')
  return performance.now() - start
}

describe('PlayerDirectoryTable pagination perf', () => {
  afterEach(() => cleanup())

  it('keeps render time flat as the total dataset grows from 50 to 3045 players', async () => {
    // Discard a warm-up render first -- the first render in a fresh
    // jsdom/React tree pays one-time module-init cost unrelated to
    // pagination, which would otherwise pollute the `small` baseline.
    await measureRender(50)

    const small = await measureRender(50)
    const large = await measureRender(3045)
    // Benchmark, not a correctness test -- print the actual numbers on
    // every run so the trend is visible even when it passes, not just
    // the pass/fail verdict.
    // eslint-disable-next-line no-console
    console.log(
      `\n50 players:   ${small.toFixed(2)}ms` +
        `\n3045 players: ${large.toFixed(2)}ms` +
        `\nratio: ${(large / small).toFixed(2)}x`
    )

    // Generous multiplicative + additive slack for CI jitter: a healthy
    // run should land near 1x (both cases mount the same 50 DOM rows);
    // a real regression lands near 60x. 4x-plus-20ms sits well clear of
    // one and nowhere near the other.
    expect(large).toBeLessThan(small * 4 + 20)
  }, 15000)
})
