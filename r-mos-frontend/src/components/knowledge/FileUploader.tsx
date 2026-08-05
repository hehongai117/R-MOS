import { FileUp, FolderUp, Loader2, Trash2, Upload } from 'lucide-react'
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

const isAccepted = (file: File) => {
  const name = file.name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))
}

/** 递归展开拖入的目录条目。readEntries 单次最多返回 100 项，必须循环读到空为止。 */
const readEntryFiles = async (entry: FileSystemEntry): Promise<File[]> => {
  if (entry.isFile) {
    const fileEntry = entry as FileSystemFileEntry
    return new Promise((resolve) => {
      fileEntry.file(
        (file) => resolve([file]),
        () => resolve([]),
      )
    })
  }
  if (entry.isDirectory) {
    const reader = (entry as FileSystemDirectoryEntry).createReader()
    const children: FileSystemEntry[] = []
    for (;;) {
      const batch = await new Promise<FileSystemEntry[]>((resolve) => {
        reader.readEntries(
          (result) => resolve(result),
          () => resolve([]),
        )
      })
      if (batch.length === 0) break
      children.push(...batch)
    }
    const nested = await Promise.all(children.map(readEntryFiles))
    return nested.flat()
  }
  return []
}

export function FileUploader({ robotId, onUploadComplete }: FileUploaderProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const inputId = useId()
  const dirInputId = useId()

  const addFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return
    setFiles((prev) => [...prev, ...Array.from(newFiles)])
  }, [])

  /**
   * 选文件夹时浏览器会把目录内所有文件都交上来（含 .DS_Store 等），
   * 这里按受支持的扩展名过滤，避免后端白名单拒收后显示一堆“失败”。
   */
  const addFilteredFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return
    addFilteredList(Array.from(newFiles))
  }, [])

  const addFilteredList = useCallback((all: File[]) => {
    const accepted = all.filter(isAccepted)
    const skipped = all.length - accepted.length
    if (accepted.length > 0) {
      setFiles((prev) => [...prev, ...accepted])
    }
    if (skipped > 0) {
      message.info(`已跳过 ${skipped} 个不支持的文件`)
    }
  }, [])

  /**
   * 拖拽时若含文件夹，dataTransfer.files 不会展开其内容，
   * 需要走 webkitGetAsEntry 递归取文件。
   */
  const handleDrop = useCallback(
    async (dt: DataTransfer) => {
      const items = Array.from(dt.items ?? [])
      const entries = items
        .map((item) => item.webkitGetAsEntry?.() ?? null)
        .filter((e): e is FileSystemEntry => e !== null)

      if (entries.length === 0 || !entries.some((e) => e.isDirectory)) {
        addFiles(dt.files)
        return
      }

      const collected = (await Promise.all(entries.map(readEntryFiles))).flat()
      addFilteredList(collected)
    },
    [addFiles, addFilteredList],
  )

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
          void handleDrop(e.dataTransfer)
        }}
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <Upload className="h-8 w-8 text-text-muted" />
          <div className="text-sm text-text-primary">
            拖拽文件或文件夹到这里，或{' '}
            <label htmlFor={inputId} className="cursor-pointer text-primary underline">
              浏览文件
            </label>
            {' / '}
            <label htmlFor={dirInputId} className="cursor-pointer text-primary underline">
              选择文件夹
            </label>
          </div>
          <div className="text-xs text-text-muted">
            支持 PDF、Word、Markdown、CAD（STEP/STL/OBJ/DAE）、GLB/GLTF、URDF、图片，单文件 ≤ 200MB
          </div>
          <div className="text-xs text-text-muted">
            <FolderUp className="mr-1 inline h-3 w-3" />
            选择文件夹会自动带上其中所有受支持的文件（如 URDF 的 meshes 目录），可多次选择累加
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
          <input
            id={dirInputId}
            data-testid="directory-input"
            className="hidden"
            type="file"
            multiple
            // 非标准属性，需通过 ref 回调落到 DOM 上（React 不识别驼峰写法）
            ref={(el) => {
              if (el) {
                el.setAttribute('webkitdirectory', '')
                el.setAttribute('directory', '')
              }
            }}
            onChange={(e) => {
              addFilteredFiles(e.target.files)
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
