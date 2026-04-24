import { useState, useEffect } from 'react'
import { listRoles, createRole, deleteRole } from '../api/roles'

export default function RolesTab({ slug }) {
  const [roles, setRoles] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState('#60a5fa')
  const [error, setError] = useState('')

  const load = () =>
    listRoles(slug)
      .then(setRoles)
      .catch(() => setError('Failed to load roles'))

  useEffect(() => {
    load()
  }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await createRole(slug, { name, color })
      setName('')
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create role')
    }
  }

  const handleDelete = async (id) => {
    await deleteRole(slug, id)
    load()
  }

  return (
    <div className="p-6 space-y-6">
      <form onSubmit={handleCreate} className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Role name</label>
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="e.g. admin"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Color</label>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-16 rounded cursor-pointer bg-gray-800 border border-gray-700"
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          Add role
        </button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Name</th>
            <th className="text-left py-2">Color</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {roles.map((role) => (
            <tr key={role.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2 text-white font-mono">{role.name}</td>
              <td className="py-2">
                <span
                  className="inline-block w-4 h-4 rounded-full"
                  style={{ backgroundColor: role.color }}
                />
              </td>
              <td className="py-2 text-right">
                <button
                  onClick={() => handleDelete(role.id)}
                  className="text-red-400 hover:text-red-300 text-xs"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
