import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import SimulatorTab from './SimulatorTab'
import * as rolesApi from '../api/roles'
import * as simulateApi from '../api/simulate'
import * as analyzeApi from '../api/analyze'

vi.mock('../api/roles')
vi.mock('../api/simulate')
vi.mock('../api/analyze')

describe('SimulatorTab', () => {
  it('shows allowed and denied resources after selecting a role', async () => {
    rolesApi.listRoles.mockResolvedValue([{ id: '1', name: 'admin', color: '#60a5fa' }])
    analyzeApi.analyzeProject.mockResolvedValue({ findings: [] })
    simulateApi.simulateRole.mockResolvedValue({
      role_id: '1',
      role_name: 'admin',
      resources: [
        {
          resource_id: 'r1',
          method: 'GET',
          path: '/users',
          allowed: true,
          granted_by_permission: 'read_users',
          granted_by_role: 'admin',
        },
        { resource_id: 'r2', method: 'DELETE', path: '/users/{id}', allowed: false },
      ],
    })
    render(<SimulatorTab slug="test" />)
    await waitFor(() => screen.getByText('admin'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    await waitFor(() => expect(screen.getByText('/users')).toBeInTheDocument())
    expect(screen.getByText('ALLOWED')).toBeInTheDocument()
    expect(screen.getByText('DENIED')).toBeInTheDocument()
  })
})
