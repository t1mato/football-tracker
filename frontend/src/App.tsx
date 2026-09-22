import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Leagues } from './pages/Leagues'
import { Teams } from './pages/Teams'
import { Players } from './pages/Players'

const queryClient = new QueryClient()

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `font-body font-bold text-base px-5 py-2.5 rounded-full ${
    isActive ? 'bg-violet-soft text-violet' : 'text-text-muted'
  }`

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <nav className="flex items-center gap-8 px-8 py-4 bg-surface border-b border-line">
          <div className="flex items-center gap-3 mr-auto">
            <img src="/logo.png" alt="" className="w-9 h-9" />
            <span className="font-display text-3xl tracking-wide">footyDB</span>
          </div>
          <div className="flex gap-2">
            <NavLink to="/" end className={navLinkClass}>
              Leagues
            </NavLink>
            <NavLink to="/teams" className={navLinkClass}>
              Clubs
            </NavLink>
            <NavLink to="/players" className={navLinkClass}>
              Players
            </NavLink>
          </div>
        </nav>
        <main className="max-w-[1040px] mx-auto px-6 py-12">
          <Routes>
            <Route path="/" element={<Leagues />} />
            <Route path="/teams" element={<Teams />} />
            <Route path="/players" element={<Players />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
