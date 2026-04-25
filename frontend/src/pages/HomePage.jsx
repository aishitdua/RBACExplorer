import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import { createProject, listProjects } from '../api/projects'

export default function HomePage() {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    listProjects().then(setProjects).catch(console.error)
  }, [])

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

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-6 sm:p-8">
      <div className="absolute top-4 right-4">
        <UserButton afterSignOutUrl="/" />
      </div>
      <div className="w-full max-w-lg space-y-10">
        <div className="text-center space-y-3">
          <h1 className="text-5xl font-black text-white tracking-tighter">RBACExplorer</h1>
          <p className="text-gray-500 text-lg">Infrastructure-as-Code for access control.</p>
        </div>

        <div className="grid grid-cols-1 gap-8">
          {/* Create Section */}
          <form
            onSubmit={handleCreate}
            className="bg-gray-900 border border-gray-800 rounded-3xl p-8 shadow-2xl space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-white">Create New Project</h2>
              <p className="text-gray-500 text-xs">Start a fresh authorization architecture</p>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl text-sm">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <input
                className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-5 py-4 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                placeholder="Project Name (e.g. Production API)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <textarea
                className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-5 py-4 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-all h-24 resize-none"
                placeholder="Project description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 rounded-2xl transition-all shadow-lg shadow-blue-600/10 active:scale-[0.98]"
            >
              Create and Open
            </button>
          </form>

          {/* Searchable Select Section */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-3xl p-8 space-y-6 relative">
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-white">Open Workspace</h2>
              <p className="text-gray-500 text-xs">
                Search for an existing project by name or slug
              </p>
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
                <svg
                  className="w-5 h-5 text-gray-500 group-focus-within:text-blue-400 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <input
                className="w-full bg-gray-950 border border-gray-800 rounded-2xl pl-14 pr-5 py-4 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all shadow-lg"
                placeholder="Search projects..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />

              {search && (
                <div className="absolute top-full left-0 right-0 mt-3 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="max-h-60 overflow-y-auto py-2">
                    {filteredProjects.length > 0 ? (
                      filteredProjects.map((project) => (
                        <button
                          key={project.id}
                          onClick={() => navigate(`/${project.slug}`)}
                          className="w-full text-left px-5 py-4 hover:bg-gray-800 flex items-center justify-between group"
                        >
                          <div>
                            <div className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors">
                              {project.name}
                            </div>
                            <div className="text-[10px] text-gray-500 font-mono tracking-tighter uppercase">
                              {project.slug}
                            </div>
                          </div>
                          <svg
                            className="w-4 h-4 text-gray-700 group-hover:text-gray-400 transition-colors"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </button>
                      ))
                    ) : (
                      <div className="px-5 py-8 text-center text-gray-600 text-sm italic">
                        No projects found matching your search.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
