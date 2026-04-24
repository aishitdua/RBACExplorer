import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL

export default function ImportTab({ slug }) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const handleFileUpload = async (e, type) => {
    const file = e.target.files[0]
    if (!file) return

    setLoading(true)
    setMessage(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const endpoint = type === 'csv' ? 'csv' : 'yaml'
      await axios.post(`${API_URL}/api/v1/projects/${slug}/import/${endpoint}`, formData)
      setMessage({ type: 'success', text: `Successfully imported ${type.toUpperCase()} file.` })
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Import failed.' })
    } finally {
      setLoading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-white">Bulk Import</h2>
        <p className="text-gray-400 text-sm">
          Bootstrap your project by uploading configuration files.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* CSV Import */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4 hover:border-gray-700 transition-colors">
          <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
            <svg
              className="w-6 h-6 text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <div className="space-y-1">
            <h3 className="text-white font-semibold">Endpoints (CSV)</h3>
            <p className="text-gray-500 text-xs">Columns: method, path, description</p>
          </div>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => handleFileUpload(e, 'csv')}
            className="hidden"
            id="csv-upload"
            disabled={loading}
          />
          <label
            htmlFor="csv-upload"
            className="block w-full text-center py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg cursor-pointer transition-colors"
          >
            Upload CSV
          </label>
        </div>

        {/* YAML Import */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4 hover:border-gray-700 transition-colors">
          <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
            <svg
              className="w-6 h-6 text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          </div>
          <div className="space-y-1">
            <h3 className="text-white font-semibold">RBAC Config (YAML)</h3>
            <p className="text-gray-500 text-xs">Define Roles, Permissions & Automated Mappings</p>
          </div>
          <input
            type="file"
            accept=".yaml,.yml"
            onChange={(e) => handleFileUpload(e, 'yaml')}
            className="hidden"
            id="yaml-upload"
            disabled={loading}
          />
          <label
            htmlFor="yaml-upload"
            className="block w-full text-center py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg cursor-pointer transition-colors"
          >
            Upload YAML
          </label>
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl text-sm font-medium ${message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}
        >
          {message.text}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center gap-3 text-gray-400 text-sm font-mono animate-pulse">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
          Processing files...
        </div>
      )}

      {/* YAML Documentation */}
      <div className="bg-gray-900/50 border border-gray-800/50 rounded-2xl p-6 space-y-4">
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
          YAML Format Example
        </h4>
        <pre className="text-[10px] sm:text-xs text-gray-400 font-mono bg-gray-950 p-4 rounded-lg border border-gray-800 overflow-x-auto">
          {`permissions:
  - name: users.read
    description: View user list
    resources:
      - method: GET
        path: /api/v1/users
roles:
  - name: Admin
    color: "#ef4444"
    permissions:
      - users.read
  - name: SuperAdmin
    parents:
      - Admin`}
        </pre>
      </div>

      <div className="pt-8 border-t border-gray-800">
        <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-center sm:text-left">
            <h4 className="text-red-400 font-semibold">Danger Zone</h4>
            <p className="text-gray-500 text-xs">
              This will permanently delete all roles, permissions, and endpoints in this project.
            </p>
          </div>
          <button
            onClick={async () => {
              if (
                confirm(
                  'Are you absolutely sure? This will wipe ALL experimental data, mappings, and roles in this project.'
                )
              ) {
                setLoading(true)
                try {
                  await axios.post(`${API_URL}/api/v1/projects/${slug}/clean`, { confirm: slug })
                  setMessage({ type: 'success', text: 'Project cleaned successfully.' })
                } catch (err) {
                  setMessage({ type: 'error', text: 'Failed to clean project.' })
                } finally {
                  setLoading(false)
                }
              }
            }}
            disabled={loading}
            className="px-6 py-2 bg-red-950/30 hover:bg-red-500 text-red-500 hover:text-white border border-red-500/30 rounded-xl text-xs font-bold uppercase tracking-wider transition-all"
          >
            Clear Project Data
          </button>
        </div>
      </div>
    </div>
  )
}
