import { FileUp, Loader2, Trash2, Upload } from 'lucide-react'
import { useCallback, useId, useState } from 'react'
import { message } from 'antd'

import { uploadRobotFiles } from '@/api/robots'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { FileUploadResponse } from '@/types/robotModel'

interface FileUploaderProps {
  robotId: number
  onUploadComplete: (result: FileUploadResponse) => void
}

const ACCEPTED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.md', '.txt',
  '.step', '.stp', '.stl', '.obj', '.dae',
  '.glb', '.gltf',
  '.urdf', '.xacro', '.xml', '.json', '.yaml', '.yml',
  '.png', '.jpg', '.jpeg',
]

export function FileUploader({ robotId, onUploadComplete }: FileUploaderProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const inputId = useId()

  const addFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return
    setFiles((prev) => [...prev, ...Array.from(newFiles)])
  }, [])

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    setProgress(0)
    try {
      const result = await uploadRobotFiles(robotId, files, setProgress)
      if (result.uploaded.length > 0) {
        message.success(`成功上传 ${result.uploaded.length} 个文件`)
      }
      if (result.failed.length > 0) {
        message.warning(`${result.failed.length} 个文件上传失败`)
      }
      setFiles([])
      onUploadComplete(result)
    } catch {
      message.error('文件上传失败')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <div className="space-y-3">
      <div
        className="rounded-xl border border-dashed border-border-default bg-bg-elevated p-5"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          addFiles(e.dataTransfer.files)
        }}
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <Upload className="h-8 w-8 text-text-muted" />
          <div className="text-sm text-text-primary">
            拖拽文件到这里，或{' '}
            <label htmlFor={inputId} className="cursor-pointer text-primary underline">
              浏览文件
            </label>
          </div>
          <div className="text-xs text-text-muted">
            支持 PDF、Word、Markdown、CAD（STEP/STL/OBJ/DAE）、GLB/GLTF、URDF、图片，单文件 ≤ 200MB
          </div>
          <input
            id={inputId}
            data-testid="file-input"
            className="hidden"
            type="file"
            multiple
            accept={ACCEPTED_EXTENSIONS.join(',')}
            onChange={(e) => {
              addFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </div>
      </div>

      {files.length > 0 && (
        <>
          <div className="space-y-1">
            {files.map((file, idx) => (
              <div
                key={`${file.name}-${idx}`}
                className="flex items-center justify-between rounded-md border border-border-subtle bg-bg-base px-3 py-2"
              >
                <div className="flex items-center gap-2 text-sm">
                  <FileUp className="h-4 w-4 text-text-muted" />
                  <span className="text-text-primary">{file.name}</span>
                  <span className="text-xs text-text-muted">
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </span>
                </div>
                <button
                  className="text-text-muted hover:text-red-500"
                  onClick={() => removeFile(idx)}
                  aria-label={`删除 ${file.name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          {uploading && (
            <div className="space-y-1">
              <div className="text-xs text-text-muted">上传进度</div>
              <Progress value={progress} />
            </div>
          )}

          <Button
            type="button"
            disabled={uploading}
            onClick={() => void handleUpload()}
          >
            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            上传文件
          </Button>
        </>
      )}
    </div>
  )
}
