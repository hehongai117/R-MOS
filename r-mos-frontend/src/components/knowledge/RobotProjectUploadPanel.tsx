import { FileUp, PackageOpen } from 'lucide-react'
import { useId, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'

interface RobotProjectUploadPanelProps {
  uploading: boolean
  uploadProgress: number
  onUpload: (payload: { file: File; brand: string; model: string; version: string }) => Promise<void> | void
}

export function RobotProjectUploadPanel({
  uploading,
  uploadProgress,
  onUpload,
}: RobotProjectUploadPanelProps) {
  const [brand, setBrand] = useState('')
  const [model, setModel] = useState('')
  const [version, setVersion] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileInputId = useId()

  const canUpload = Boolean(file && brand.trim() && model.trim())

  const handleFilePick = (nextFile: File | null) => {
    setFile(nextFile)
  }

  const submit = async () => {
    if (!file || !brand.trim() || !model.trim()) {
      return
    }
    await onUpload({
      file,
      brand: brand.trim(),
      model: model.trim(),
      version: version.trim(),
    })
    setFile(null)
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <label className="space-y-2 text-sm text-text-primary">
          <span>机器人品牌</span>
          <Input
            aria-label="机器人品牌"
            placeholder="例如 Fourier"
            value={brand}
            onChange={(event) => setBrand(event.target.value)}
          />
        </label>
        <label className="space-y-2 text-sm text-text-primary">
          <span>机器人型号</span>
          <Input
            aria-label="机器人型号"
            placeholder="例如 N1"
            value={model}
            onChange={(event) => setModel(event.target.value)}
          />
        </label>
        <label className="space-y-2 text-sm text-text-primary">
          <span>版本标识</span>
          <Input
            aria-label="版本标识"
            placeholder="例如 2026-Q1"
            value={version}
            onChange={(event) => setVersion(event.target.value)}
          />
        </label>
      </div>

      <div
        className="rounded-xl border border-dashed border-border-default bg-bg-elevated p-5"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          handleFilePick(event.dataTransfer.files?.[0] ?? null)
        }}
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
              <PackageOpen className="h-4 w-4" />
              机器人项目包上传
            </div>
            <div className="mt-1 text-xs text-text-muted">
              支持 zip 多文件包。建议包含文档、装配结构和 viewer-ready 模型。
            </div>
            <div className="mt-2 text-sm text-text-primary">
              {file ? `已选择：${file.name}` : '拖拽项目包到这里，或使用下方按钮选择文件'}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <label
              className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border-default bg-bg-base px-4 py-2 text-sm text-text-primary"
              htmlFor={fileInputId}
            >
              <FileUp className="h-4 w-4" />
              选择项目包
            </label>
            <input
              id={fileInputId}
              className="hidden"
              type="file"
              onChange={(event) => {
                handleFilePick(event.target.files?.[0] ?? null)
                event.target.value = ''
              }}
            />
            <Button disabled={!canUpload || uploading} type="button" onClick={() => void submit()}>
              上传项目包
            </Button>
          </div>
        </div>

        {uploading || uploadProgress > 0 ? (
          <div className="mt-4 space-y-2">
            <div className="text-xs text-text-muted">ingest 进度</div>
            <Progress value={uploadProgress} />
          </div>
        ) : null}
      </div>
    </div>
  )
}
