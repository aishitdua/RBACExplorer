import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { listRoles, addParent, removeParent, deleteRole } from '../api/roles'
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
  const [rolesList, setRolesList] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [roles, permissions] = await Promise.all([listRoles(slug), listPermissions(slug)])
      setRolesList(roles)
      
      const elements = []
      const moduleNodes = new Set()

      // Role nodes
      roles.forEach(role => {
        elements.push({
          data: { id: `role-${role.id}`, label: role.name, type: 'role', color: role.color || '#3b82f6' },
        })
      })

      // Permission nodes and Module Parents
      if (showPermissions) {
        roles.forEach(role => {
          (role.permissions || []).forEach(perm => {
            const moduleId = `mod-${perm.module}`
            if (!moduleNodes.has(moduleId)) {
              elements.push({
                data: { id: moduleId, label: perm.module.toUpperCase(), type: 'module' }
              })
              moduleNodes.add(moduleId)
            }
            
            if (!elements.find(e => e.data.id === `perm-${perm.id}`)) {
              elements.push({
                data: { 
                  id: `perm-${perm.id}`, 
                  label: perm.name.split('.').pop(), 
                  type: 'permission', 
                  parent: moduleId 
                },
              })
            }
          })
        })
      }

      // Edges
      roles.forEach(role => {
        if (role.parents) {
          role.parents.forEach(parentId => {
            elements.push({ 
              data: { id: `inh-${parentId}-${role.id}`, source: `role-${parentId}`, target: `role-${role.id}`, type: 'inheritance' } 
            })
          })
        }
        
        if (showPermissions && role.permissions) {
          role.permissions.forEach(perm => {
            elements.push({
              data: { id: `link-${role.id}-${perm.id}`, source: `role-${role.id}`, target: `perm-${perm.id}`, type: 'permission-link' }
            })
          })
        }
      })

      if (cyRef.current) {
        cyRef.current.json({ elements })
        cyRef.current.layout({ 
          name: 'breadthfirst', 
          directed: true, 
          padding: 50,
          spacingFactor: 2.0,
          animate: true,
          nodeDimensionsIncludeLabels: true
        }).run()
      } else {
        const cy = cytoscape({
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
                'font-size': '8px',
                width: 40,
                height: 40,
                'border-width': 2,
                'border-color': '#000',
                'z-index': 10
              },
            },
            {
              selector: 'node[type="module"]',
              style: {
                label: 'data(label)',
                'background-color': '#1e1e1e',
                'background-opacity': 0.4,
                'border-width': 1,
                'border-color': '#333',
                'border-style': 'dashed',
                'text-valign': 'top',
                'text-halign': 'center',
                'font-size': '10px',
                'color': '#666',
                'padding': '20px',
                'shape': 'roundrectangle'
              }
            },
            {
              selector: 'node[type="permission"]',
              style: {
                label: 'data(label)',
                'background-color': '#be185d',
                color: '#fff',
                'text-valign': 'center',
                'font-family': 'monospace',
                'font-size': '6px',
                width: 15,
                height: 15,
                shape: 'ellipse',
              },
            },
            {
              selector: 'edge',
              style: {
                'curve-style': 'bezier',
                'target-arrow-shape': 'triangle',
                'arrow-scale': 0.8,
                'opacity': 0.6
              },
            },
            {
              selector: 'edge[type="inheritance"]',
              style: {
                width: 3,
                'line-color': '#4b5563',
                'target-arrow-color': '#4b5563',
              },
            },
            {
              selector: 'edge[type="permission-link"]',
              style: {
                'line-color': '#ec4899',
                'target-arrow-color': '#ec4899',
                'line-style': 'dashed',
                width: 1,
              },
            },
            {
              selector: ':selected',
              style: { 'border-color': '#60a5fa', 'border-width': 4 },
            },
          ],
          layout: { 
            name: 'breadthfirst', 
            directed: true,
            spacingFactor: 2.0,
            padding: 50
          },
        })

        cy.on('tap', 'node', (e) => {
          const node = e.target
          if (node.data('type') === 'module') return
          
          const nodeId = node.id()
          const rawId = nodeId.includes('-') ? nodeId.substring(nodeId.indexOf('-') + 1) : nodeId

          setSelected({ 
            id: rawId,
            label: node.data('label'), 
            type: node.data('type'),
            nodeId: nodeId
          })
        })

        cy.on('tap', (e) => {
          if (e.target === cy) setSelected(null)
        })

        cyRef.current = cy
      }
    } catch (err) {
      console.error('Fetch failed', err)
    } finally {
      setLoading(false)
    }
  }, [slug, showPermissions])

  useEffect(() => {
    fetchData()
    return () => { if (cyRef.current) cyRef.current.destroy(); cyRef.current = null }
  }, [fetchData])

  const handleExportYaml = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/projects/${slug}/export/yaml`)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${slug}-rbac.yaml`
      a.click()
    } catch (err) {
      console.error('Export failed', err)
    }
  }

  const handleAddParent = async (parentId) => {
    if (!selected || selected.type !== 'role') return
    try {
      await addParent(slug, selected.id, parentId)
      fetchData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add dependency')
    }
  }

  const handleDelete = async () => {
    if (!selected || selected.type !== 'role' || !confirm('Delete this role?')) return
    try {
      await deleteRole(slug, selected.id)
      setSelected(null)
      fetchData()
    } catch (err) {
      console.error(err)
    }
  }

  const selectedRoleData = selected?.type === 'role' ? rolesList.find(r => r.id == selected.id) : null

  return (
    <div className="relative h-full overflow-hidden">
      <div id="cy" ref={containerRef} className="w-full h-full bg-gray-950" />
      
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        <button
          onClick={() => setShowPermissions(v => !v)}
          className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-lg ${showPermissions ? 'bg-blue-600 text-white shadow-blue-600/20' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
        >
          {showPermissions ? 'Hide Permissions' : 'Show Permissions'}
        </button>
        
        <button
          onClick={handleExportYaml}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 shadow-lg"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          Export YAML
        </button>
      </div>

      {selected && (
        <div className="absolute top-4 right-4 bottom-4 w-80 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-3xl shadow-2xl p-6 flex flex-col gap-6 animate-in slide-in-from-right-8 duration-300">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-500">{selected.type} Editor</span>
            <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">Entity Name</label>
              <div className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-white font-mono text-sm">
                {selected.label}
              </div>
            </div>

            {selected.type === 'role' && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">Inherit From (Parent)</label>
                <select 
                  className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500 transition-colors cursor-pointer appearance-none"
                  onChange={(e) => handleAddParent(e.target.value)}
                  value=""
                >
                  <option value="" disabled>Choose a role to inherit from...</option>
                  {rolesList
                    .filter(r => r.id != selected.id && !selectedRoleData?.parents?.includes(r.id))
                    .map(r => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))
                  }
                </select>
              </div>
            )}

            {selectedRoleData?.parents?.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-500 uppercase ml-1">Current Parents</label>
                <div className="flex flex-wrap gap-2">
                  {selectedRoleData.parents.map(pid => {
                    const pname = rolesList.find(r => r.id == pid)?.name || pid
                    return (
                      <div key={pid} className="bg-gray-800 px-2 py-1 rounded text-[10px] text-gray-300 flex items-center gap-1">
                        {pname}
                        <button 
                          onClick={async () => { await removeParent(slug, selected.id, pid); fetchData() }}
                          className="hover:text-red-500"
                        >
                          ×
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="mt-auto pt-6 border-t border-gray-800 flex gap-2">
            <button 
              onClick={handleDelete}
              className="flex-1 bg-gray-800 hover:bg-red-950 hover:text-red-400 text-gray-300 font-bold py-3 rounded-xl text-xs transition-colors"
            >
              Delete Entity
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
