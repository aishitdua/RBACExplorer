import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import RolesTab from './RolesTab'
import * as rolesApi from '../api/roles'

vi.mock('../api/roles')

describe('RolesTab', () => {
  it('renders role list', async () => {
    rolesApi.listRoles.mockResolvedValue([
      { id: '1', name: 'admin', description: '', color: '#60a5fa' },
      { id: '2', name: 'viewer', description: '', color: '#34d399' },
    ])
    render(<RolesTab slug="test" />)
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument())
    expect(screen.getByText('viewer')).toBeInTheDocument()
  })
})
