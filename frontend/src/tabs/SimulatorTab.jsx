import { useState, useEffect } from 'react'
import { listRoles } from '../api/roles'
import { simulateRole } from '../api/simulate'
import { analyzeProject } from '../api/analyze'
import ConflictPanel from '../components/ConflictPanel'
import CodeExportModal from '../components/CodeExportModal'

const METHOD_COLORS = {
  GET: 'text-green-400',
  POST: 'text-blue-400',
  PUT: 'text-yellow-400',
  PATCH: 'text-orange-400',
  DELETE: 'text-red-400',
}

export default function SimulatorTab({ slug }) {
  const [roles, setRoles] = useState([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [simulation, setSimulation] = useState(null)
  const [findings, setFindings] = useState([])
  const [showExport, setShowExport] = useState(false)

  useEffect(() => {
    listRoles(slug).then(setRoles)
    analyzeProject(slug).then((r) => setFindings(r.findings))
  }, [slug])

  const handleRoleChange = async (e) => {
    const roleId = e.target.value
    setSelectedRoleId(roleId)
    if (roleId) {
      const result = await simulateRole(slug, roleId)
      setSimulation(result)
    } else {
      setSimulation(null)
    }
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {showExport && <CodeExportModal slug={slug} onClose={() => setShowExport(false)} />}
      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Simulate access as role</label>
          <select
            value={selectedRoleId}
            onChange={handleRoleChange}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full"
          >
            <option value="">Select a role…</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setShowExport(true)}
          className="mt-5 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm"
        >
          Export FastAPI code
        </button>
      </div>

      {simulation && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2">Method</th>
              <th className="text-left py-2">Path</th>
              <th className="text-left py-2">Access</th>
              <th className="text-left py-2">Granted by</th>
            </tr>
          </thead>
          <tbody>
            {simulation.resources.map((res) => (
              <tr key={res.resource_id} className="border-b border-gray-800 hover:bg-gray-900">
                <td className="py-2">
                  <span
                    className={`font-mono font-bold text-xs ${METHOD_COLORS[res.method] || 'text-gray-400'}`}
                  >
                    {res.method}
                  </span>
                </td>
                <td className="py-2 text-white font-mono">{res.path}</td>
                <td className="py-2">
                  {res.allowed ? (
                    <span className="text-green-400 font-semibold text-xs">ALLOWED</span>
                  ) : (
                    <span className="text-red-400 font-semibold text-xs">DENIED</span>
                  )}
                </td>
                <td className="py-2 text-gray-500 text-xs">
                  {res.allowed ? `${res.granted_by_permission} (via ${res.granted_by_role})` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-3">Conflicts & Anomalies</h3>
        <ConflictPanel findings={findings} />
      </div>
    </div>
  )
}
