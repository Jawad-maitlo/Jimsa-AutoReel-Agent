import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EmptyState, Modal, ProgressBar, StatusPill } from '@/components/UI'

describe('shared interface states', () => {
  it('exposes progress and job status', () => {
    render(<><ProgressBar value={42} /><StatusPill status="failed" /></>)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42')
    expect(screen.getByText('failed')).toBeInTheDocument()
  })
  it('renders useful empty-state actions', () => {
    const action = vi.fn()
    render(<EmptyState icon={<span>i</span>} title="No videos" description="Import one" action={<button onClick={action}>Import</button>} />)
    fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(action).toHaveBeenCalledOnce()
  })
  it('closes dialogs with escape and explicit button', () => {
    const close = vi.fn()
    render(<Modal title="Preview" onClose={close}><p>Content</p></Modal>)
    fireEvent.keyDown(window, { key: 'Escape' })
    fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }))
    expect(close).toHaveBeenCalledTimes(2)
  })
})
