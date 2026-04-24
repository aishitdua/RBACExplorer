import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api/projects'

export default function HomePage() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [openSlug, setOpenSlug] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const project = await createProject({ name, description })
      navigate(`/${project.slug}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">RBACExplorer</h1>
          <p className="mt-2 text-gray-400">Design and visualise your app's access control</p>
        </div>

        <form onSubmit={handleCreate} className="space-y-4 bg-gray-900 p-6 rounded-xl border border-gray-800">
          <h2 className="text-lg font-semibold text-white">Create a project</h2>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Create project
          </button>
        </form>

        <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 space-y-4">
          <h2 className="text-lg font-semibold text-white">Open existing project</h2>
          <div className="flex gap-2">
            <input
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              placeholder="Project slug"
              value={openSlug}
              onChange={(e) => setOpenSlug(e.target.value)}
            />
            <button
              onClick={() => openSlug && navigate(`/${openSlug}`)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Open
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
