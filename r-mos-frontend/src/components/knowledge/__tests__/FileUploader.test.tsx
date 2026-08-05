import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FileUploader } from '../FileUploader'

describe('FileUploader', () => {
  it('renders drop zone', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    expect(screen.getByText(/拖拽文件或文件夹到这里/)).toBeInTheDocument()
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

  it('exposes a directory picker input', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    const dirInput = screen.getByTestId('directory-input') as HTMLInputElement
    // webkitdirectory 是非标准属性，React 通过 DOM 属性设置，断言实际 attribute
    expect(dirInput.hasAttribute('webkitdirectory')).toBe(true)
  })

  it('keeps only whitelisted files when a folder is picked', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    const dirInput = screen.getByTestId('directory-input') as HTMLInputElement
    const good = new File(['x'], 'base_link.STL', { type: '' })
    const junk = new File(['x'], '.DS_Store', { type: '' })
    fireEvent.change(dirInput, { target: { files: [good, junk] } })

    expect(screen.getByText('base_link.STL')).toBeInTheDocument()
    expect(screen.queryByText('.DS_Store')).not.toBeInTheDocument()
  })

  it('accumulates files across multiple selections instead of replacing', () => {
    render(<FileUploader robotId={1} onUploadComplete={vi.fn()} />)
    const fileInput = screen.getByTestId('file-input') as HTMLInputElement
    fireEvent.change(fileInput, {
      target: { files: [new File(['x'], 'robot.urdf', { type: '' })] },
    })
    const dirInput = screen.getByTestId('directory-input') as HTMLInputElement
    fireEvent.change(dirInput, {
      target: { files: [new File(['x'], 'link1.stl', { type: '' })] },
    })

    expect(screen.getByText('robot.urdf')).toBeInTheDocument()
    expect(screen.getByText('link1.stl')).toBeInTheDocument()
  })
})
