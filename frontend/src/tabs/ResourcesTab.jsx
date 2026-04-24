import { useState, useEffect } from 'react'
import { listResources, createResource, deleteResource } from '../api/resources'
import OpenAPIImportModal from '../components/OpenAPIImportModal'

const METHOD_COLORS = { GET: 'text-green-400', POST: 'text-blue-400', PUT: 'text-yellow-400', PATCH: 'text-orange-400', DELETE: 'text-red-400' }

export default function ResourcesTab({ slug }) {
  const [resources, setResources] = useState([])
  const [method, setMethod] = useState('GET')
  const [path, setPath] = useState('')
  const [showImport, setShowImport] = useState(false)

  const load = () => listResources(slug).then(setResources)
  useEffect(() => { load() }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createResource(slug, { method, path })
    setPath('')
    load()
  }

  return (
    <div className="p-6 space-y-6">
      {showImport && <OpenAPIImportModal slug={slug} onClose={() => setShowImport(false)} onImported={load} />}
      <div className="flex gap-3 justify-between items-end">
        <form onSubmit={handleCreate} className="flex gap-3 flex-1">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          >
            {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => <option key={m}>{m}</option>)}
          </select>
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="/users/{id}"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            required
          />
          <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Add</button>
        </form>
        <button onClick={() => setShowImport(true)} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm">Import OpenAPI</button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Method</th>
            <th className="text-left py-2">Path</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {resources.map(res => (
            <tr key={res.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2">
                <span className={`font-mono font-bold text-xs ${METHOD_COLORS[res.method] || 'text-gray-400'}`}>{res.method}</span>
              </td>
              <td className="py-2 text-white font-mono">{res.path}</td>
              <td className="py-2 text-right">
                <button onClick={() => deleteResource(slug, res.id).then(load)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
