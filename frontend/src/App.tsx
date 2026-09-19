import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Leagues } from './pages/Leagues'
import { Teams } from './pages/Teams'
import { Players } from './pages/Players'

const queryClient = new QueryClient()

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <nav className="font-body">
          <Link to="/">Leagues</Link>
          <Link to="/teams">Teams</Link>
          <Link to="/players">Players</Link>
        </nav>
        <Routes>
          <Route path="/" element={<Leagues />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/players" element={<Players />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
