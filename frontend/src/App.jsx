import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { SignedIn, SignedOut, RedirectToSignIn, useAuth } from '@clerk/clerk-react'
import HomePage from './pages/HomePage'
import WorkspacePage from './pages/WorkspacePage'
import { setAuthToken } from './api/client'

function TokenSync() {
  const { getToken, isSignedIn } = useAuth()
  useEffect(() => {
    if (!isSignedIn) return
    const sync = async () => setAuthToken(await getToken())
    sync()
    const id = setInterval(sync, 55 * 1000) // refresh before 60s expiry
    return () => clearInterval(id)
  }, [isSignedIn, getToken])
  return null
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <SignedIn>
        <TokenSync />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/:slug" element={<WorkspacePage />} />
        </Routes>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </div>
  )
}
