import { useState, useEffect } from 'react'
import { listPermissions, createPermission, deletePermission, assignPermissionToRole, mapPermissionToResource } from '../api/permissions'
import { listRoles } from '../api/roles'
import { listResources } from '../api/resources'

export default function PermissionsTab({ slug }) {
  const [permissions, setPermissions] = useState([])
  const [roles, setRoles] = useState([])
  const [resources, setResources] = useState([])
  const [name, setName] = useState('')

  const load = () => Promise.all([
    listPermissions(slug).then(setPermissions),
    listRoles(slug).then(setRoles),
    listResources(slug).then(setResources),
  ])

  useEffect(() => { load() }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createPermission(slug, { name })
    setName('')
    load()
  }

  return (
    <div className="p-6 space-y-6">
      <form onSubmit={handleCreate} className="flex gap-3">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          placeholder="e.g. read_users"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Add permission</button>
      </form>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Permission</th>
            <th className="text-left py-2">Assign to role</th>
            <th className="text-left py-2">Map to endpoint</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {permissions.map(perm => (
            <tr key={perm.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2 text-white font-mono">{perm.name}</td>
              <td className="py-2">
                <select
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                  onChange={(e) => e.target.value && assignPermissionToRole(slug, e.target.value, perm.id)}
                  defaultValue=""
                >
                  <option value="">Assign to role…</option>
                  {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              </td>
              <td className="py-2">
                <select
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                  onChange={(e) => e.target.value && mapPermissionToResource(slug, perm.id, e.target.value)}
                  defaultValue=""
                >
                  <option value="">Map to endpoint…</option>
                  {resources.map(r => <option key={r.id} value={r.id}>{r.method} {r.path}</option>)}
                </select>
              </td>
              <td className="py-2 text-right">
                <button onClick={() => deletePermission(slug, perm.id).then(load)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
