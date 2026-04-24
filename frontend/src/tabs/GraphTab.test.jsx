import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import GraphTab from './GraphTab'
import * as rolesApi from '../api/roles'
import * as permissionsApi from '../api/permissions'

vi.mock('../api/roles')
vi.mock('../api/permissions')

// Cytoscape is a DOM library — mock it for unit tests
vi.mock('cytoscape', () => ({ default: vi.fn(() => ({ add: vi.fn(), layout: vi.fn(() => ({ run: vi.fn() })), on: vi.fn(), destroy: vi.fn() })) }))
vi.mock('cytoscape-fcose', () => ({ default: vi.fn() }))

describe('GraphTab', () => {
  it('renders graph container', async () => {
    rolesApi.listRoles.mockResolvedValue([])
    permissionsApi.listPermissions.mockResolvedValue([])
    render(<GraphTab slug="test" />)
    await waitFor(() => expect(document.getElementById('cy')).toBeInTheDocument())
  })
})
