import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProject } from '../api/projects'
import GraphTab from '../tabs/GraphTab'
import RolesTab from '../tabs/RolesTab'
import PermissionsTab from '../tabs/PermissionsTab'
import ResourcesTab from '../tabs/ResourcesTab'
import SimulatorTab from '../tabs/SimulatorTab'
import ImportTab from '../tabs/ImportTab'

const TABS = ['Graph', 'Roles', 'Permissions', 'Resources', 'Simulator', 'Import']

export default function WorkspacePage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [activeTab, setActiveTab] = useState('Graph')
  const [error, setError] = useState('')

  useEffect(() => {
    getProject(slug)
      .then(setProject)
      .catch(() => setError('Project not found'))
  }, [slug])

  if (error) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-4">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/')} className="text-blue-400 hover:underline">Go home</button>
      </div>
    </div>
  )

  if (!project) return <div className="flex items-center justify-center min-h-screen text-gray-500">Loading...</div>

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center gap-6 px-6 py-3 bg-gray-900 border-b border-gray-800">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white text-sm">← Home</button>
        <h1 className="text-white font-semibold">{project.name}</h1>
        <span className="text-gray-500 text-sm font-mono">{slug}</span>
        <nav className="ml-auto flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'Graph' && <GraphTab slug={slug} />}
        {activeTab === 'Roles' && <RolesTab slug={slug} />}
        {activeTab === 'Permissions' && <PermissionsTab slug={slug} />}
        {activeTab === 'Resources' && <ResourcesTab slug={slug} />}
        {activeTab === 'Simulator' && <SimulatorTab slug={slug} />}
        {activeTab === 'Import' && <ImportTab slug={slug} />}
      </main>
    </div>
  )
}
