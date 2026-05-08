// r-mos-frontend/src/components/knowledge/__tests__/AddRobotDialog.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AddRobotDialog } from '../AddRobotDialog'

describe('AddRobotDialog', () => {
  it('renders form fields when open', () => {
    render(<AddRobotDialog open onClose={vi.fn()} onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('品牌')).toBeInTheDocument()
    expect(screen.getByLabelText('型号')).toBeInTheDocument()
    expect(screen.getByLabelText('版本')).toBeInTheDocument()
    expect(screen.getByLabelText('描述')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(<AddRobotDialog open={false} onClose={vi.fn()} onSubmit={vi.fn()} />)
    expect(screen.queryByLabelText('品牌')).not.toBeInTheDocument()
  })

  it('disables submit when required fields are empty', () => {
    render(<AddRobotDialog open onClose={vi.fn()} onSubmit={vi.fn()} />)
    const submitBtn = screen.getByRole('button', { name: '创建' })
    expect(submitBtn).toBeDisabled()
  })

  it('calls onSubmit with form data when submitted', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<AddRobotDialog open onClose={vi.fn()} onSubmit={onSubmit} />)

    fireEvent.change(screen.getByLabelText('品牌'), { target: { value: 'UBTech' } })
    fireEvent.change(screen.getByLabelText('型号'), { target: { value: 'Walker X' } })
    fireEvent.change(screen.getByLabelText('版本'), { target: { value: '2.0' } })
    fireEvent.change(screen.getByLabelText('描述'), { target: { value: '测试描述' } })

    const submitBtn = screen.getByRole('button', { name: '创建' })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        brand: 'UBTech',
        model_name: 'Walker X',
        version: '2.0',
        description: '测试描述',
      })
    })
  })

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn()
    render(<AddRobotDialog open onClose={onClose} onSubmit={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(onClose).toHaveBeenCalled()
  })
})
