import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FileUploader } from '../FileUploader'

describe('FileUploader', () => {
  it('renders drop zone', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    expect(screen.getByText(/拖拽文件到这里/)).toBeInTheDocument()
  })

  it('shows selected files after selection', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    const input = screen.getByTestId('file-input') as HTMLInputElement
    const file = new File(['test'], 'manual.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText('manual.pdf')).toBeInTheDocument()
  })

  it('shows upload button only when files are selected', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    expect(screen.queryByRole('button', { name: '上传文件' })).not.toBeInTheDocument()
    const input = screen.getByTestId('file-input') as HTMLInputElement
    const file = new File(['test'], 'manual.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByRole('button', { name: '上传文件' })).toBeInTheDocument()
  })

  it('displays accepted file types hint', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    expect(screen.getByText(/PDF.*CAD.*GLB/i)).toBeInTheDocument()
  })
})
