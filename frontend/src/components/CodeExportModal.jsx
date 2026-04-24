import { useState, useEffect } from 'react'
import { exportFastapi } from '../api/export_'

export default function CodeExportModal({ slug, onClose }) {
  const [code, setCode] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    exportFastapi(slug).then(setCode)
  }, [slug])

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold">FastAPI code export</h2>
          <div className="flex gap-2">
            <button onClick={handleCopy} className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg text-sm">
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-white px-3 py-1.5">Close</button>
          </div>
        </div>
        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 font-mono overflow-auto max-h-96 whitespace-pre-wrap">{code}</pre>
      </div>
    </div>
  )
}
