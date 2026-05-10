import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
    ModelErrorFallback,
    ModelLoadingFallback,
} from '@/components/Viewer3D/DynamicModelLoader'

// Mock @react-three/drei so Html renders its children into the DOM
// and useProgress returns a fixed progress value
vi.mock('@react-three/drei', () => ({
    Html: ({ children }: { children: React.ReactNode; center?: boolean }) => <>{children}</>,
    useProgress: () => ({ progress: 50 }),
}))

describe('ModelErrorFallback', () => {
    it('renders the default error message', () => {
        render(<ModelErrorFallback />)
        expect(screen.getByText('模型加载失败')).toBeTruthy()
        expect(screen.getByText('请检查机器人是否已上传 3D 模型文件')).toBeTruthy()
    })

    it('renders a custom error message', () => {
        render(<ModelErrorFallback message="自定义错误信息" />)
        expect(screen.getByText('自定义错误信息')).toBeTruthy()
    })
})

describe('ModelLoadingFallback', () => {
    it('renders progress percentage text', () => {
        render(<ModelLoadingFallback />)
        expect(screen.getByText('50%')).toBeTruthy()
    })
})
