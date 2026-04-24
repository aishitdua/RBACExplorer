import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { listRoles } from '../api/roles'
import { listPermissions } from '../api/permissions'

// Guard against mocked cytoscape in tests
try {
  if (typeof cytoscape.use === 'function') cytoscape.use(fcose)
} catch (_) {}

export default function GraphTab({ slug }) {
  const cyRef = useRef(null)
  const containerRef = useRef(null)
  const [selected, setSelected] = useState(null)
  const [showPermissions, setShowPermissions] = useState(false)

  useEffect(() => {
    let cy
    Promise.all([listRoles(slug), listPermissions(slug)]).then(([roles, permissions]) => {
      const elements = []

      // Role nodes
      roles.forEach(role => {
        elements.push({
          data: { id: role.id, label: role.name, type: 'role', color: role.color },
        })
      })

      // Inheritance edges from parents array if available
      roles.forEach(role => {
        if (role.parents) {
          role.parents.forEach(parentId => {
            elements.push({ data: { id: `${parentId}-${role.id}`, source: parentId, target: role.id, type: 'inheritance' } })
          })
        }
      })

      cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node[type="role"]',
            style: {
              label: 'data(label)',
              'background-color': 'data(color)',
              color: '#fff',
              'text-valign': 'center',
              'font-family': 'monospace',
              'font-size': '12px',
              width: 60,
              height: 60,
              'border-width': 2,
              'border-color': '#1e293b',
            },
          },
          {
            selector: 'edge[type="inheritance"]',
            style: {
              width: 2,
              'line-color': '#334155',
              'target-arrow-color': '#334155',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
            },
          },
          {
            selector: ':selected',
            style: { 'border-color': '#60a5fa', 'border-width': 3 },
          },
        ],
        layout: { name: 'fcose', animate: true, randomize: false, nodeRepulsion: 4500 },
      })

      cyRef.current = cy

      cy.on('tap', 'node', (e) => {
        const node = e.target
        setSelected({ id: node.id(), label: node.data('label'), type: node.data('type') })
      })

      cy.on('tap', (e) => {
        if (e.target === cy) setSelected(null)
      })
    })

    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [slug])

  return (
    <div className="relative h-full">
      <div id="cy" ref={containerRef} className="w-full h-full bg-gray-950" />
      <div className="absolute top-4 left-4 flex gap-2">
        <button
          onClick={() => setShowPermissions(v => !v)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${showPermissions ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
        >
          Show permissions
        </button>
      </div>
      {selected && (
        <div className="absolute top-4 right-4 bg-gray-900 border border-gray-700 rounded-xl p-4 w-64 space-y-2">
          <h3 className="text-white font-semibold font-mono">{selected.label}</h3>
          <p className="text-gray-400 text-xs capitalize">{selected.type}</p>
        </div>
      )}
    </div>
  )
}
