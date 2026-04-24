import { useState } from 'react'
import { importOpenapi } from '../api/import_'

export default function OpenAPIImportModal({ slug, onClose, onImported }) {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleImport = async () => {
    setError('')
    try {
      const json = JSON.parse(text)
      const res = await importOpenapi(slug, json)
      setResult(res)
      onImported()
    } catch (err) {
      setError(err.message || 'Invalid JSON or import failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg space-y-4">
        <h2 className="text-white font-semibold">Import from OpenAPI spec</h2>
        <p className="text-gray-400 text-sm">Paste your OpenAPI 3.x JSON below. All paths and methods will be imported as resources.</p>
        <textarea
          className="w-full h-48 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500"
          placeholder='{ "openapi": "3.0.0", "paths": { ... } }'
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {result && <p className="text-green-400 text-sm">Created {result.created}, skipped {result.skipped}</p>}
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="text-gray-400 hover:text-white px-4 py-2">Cancel</button>
          <button onClick={handleImport} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Import</button>
        </div>
      </div>
    </div>
  )
}
