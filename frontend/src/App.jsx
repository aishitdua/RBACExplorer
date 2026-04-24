import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import WorkspacePage from './pages/WorkspacePage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:slug" element={<WorkspacePage />} />
      </Routes>
    </div>
  )
}
