const TYPE_LABELS = {
  orphaned_permission: 'Orphaned permission',
  empty_role: 'Empty role',
  redundant_assignment: 'Redundant assignment',
  permission_shadowing: 'Permission shadowing',
  circular_inheritance: 'Circular inheritance',
}

export default function ConflictPanel({ findings }) {
  if (!findings.length)
    return <div className="text-green-400 text-sm py-2">No conflicts detected</div>

  return (
    <div className="space-y-2">
      {findings.map((f, i) => (
        <div
          key={i}
          className="flex items-start gap-3 bg-yellow-950/40 border border-yellow-800/40 rounded-lg px-4 py-3"
        >
          <span className="text-yellow-400 mt-0.5">⚠</span>
          <div>
            <p className="text-yellow-300 text-sm font-medium">{TYPE_LABELS[f.type] || f.type}</p>
            <p className="text-yellow-600 text-xs mt-0.5">
              {Object.entries(f.detail)
                .map(([k, v]) => `${k}: ${v}`)
                .join(' · ')}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
