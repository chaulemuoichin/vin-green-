import { Routes, Route, Navigate } from 'react-router-dom'
import { PersonaProvider } from './context/PersonaContext'
import Dashboard from './pages/Dashboard'
import MobileView from './pages/MobileView'

export default function App() {
  return (
    <PersonaProvider>
      <Routes>
        <Route path="/"       element={<Dashboard />} />
        <Route path="/mobile" element={<MobileView />} />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </PersonaProvider>
  )
}
