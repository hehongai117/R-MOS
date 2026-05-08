// r-mos-frontend/src/components/knowledge/AddRobotDialog.tsx
import { Modal } from 'antd'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { RobotModelCreateRequest } from '@/types/robotModel'

interface AddRobotDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: RobotModelCreateRequest) => Promise<void>
  submitting?: boolean
}

export function AddRobotDialog({ open, onClose, onSubmit, submitting = false }: AddRobotDialogProps) {
  const [brand, setBrand] = useState('')
  const [modelName, setModelName] = useState('')
  const [version, setVersion] = useState('')
  const [description, setDescription] = useState('')

  const canSubmit = brand.trim().length > 0 && modelName.trim().length > 0

  const handleSubmit = async () => {
    if (!canSubmit) return
    await onSubmit({
      brand: brand.trim(),
      model_name: modelName.trim(),
      version: version.trim() || undefined,
      description: description.trim() || undefined,
    })
    // 重置表单
    setBrand('')
    setModelName('')
    setVersion('')
    setDescription('')
  }

  const handleClose = () => {
    setBrand('')
    setModelName('')
    setVersion('')
    setDescription('')
    onClose()
  }

  if (!open) return null

  return (
    <Modal
      title="添加机器人"
      open={open}
      onCancel={handleClose}
      footer={null}
      destroyOnClose
      getContainer={false}
    >
      <div className="space-y-4 pt-2">
        <label className="block space-y-1.5">
          <span className="text-sm text-text-primary" id="add-robot-brand">品牌</span>
          <Input
            aria-label="品牌"
            placeholder="例如 优必选、宇树、R-MOS"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm text-text-primary" id="add-robot-model">型号</span>
          <Input
            aria-label="型号"
            placeholder="例如 Walker X、H1、ATOM-01"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm text-text-primary" id="add-robot-version">版本</span>
          <Input
            aria-label="版本"
            placeholder="例如 1.0、2026-Q1"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm text-text-primary" id="add-robot-desc">描述</span>
          <Textarea
            aria-label="描述"
            placeholder="机器人描述（可选）"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" type="button" onClick={handleClose}>
            取消
          </Button>
          <Button
            type="button"
            disabled={!canSubmit || submitting}
            onClick={() => void handleSubmit()}
          >
            创建
          </Button>
        </div>
      </div>
    </Modal>
  )
}
