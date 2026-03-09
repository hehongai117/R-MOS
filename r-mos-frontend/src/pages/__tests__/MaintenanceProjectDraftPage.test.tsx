import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { clientGetMock, clientPostMock, navigateMock } = vi.hoisted(() => ({
  clientGetMock: vi.fn(),
  clientPostMock: vi.fn(),
  navigateMock: vi.fn(),
}))

vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  default: {
    get: clientGetMock,
    post: clientPostMock,
    patch: vi.fn(),
  },
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

import MaintenanceProjectDraftPage from '@/pages/MaintenanceProjectDraftPage'

describe('MaintenanceProjectDraftPage', () => {
  beforeEach(() => {
    clientGetMock.mockReset()
    clientPostMock.mockReset()
    navigateMock.mockReset()
    window.sessionStorage.clear()

    clientGetMock.mockResolvedValue({
      data: {
        projects: [
          {
            project_id: 'project-fourier-n1',
            robot_key: 'fourier-n1-runtime',
            brand: 'Fourier',
            model: 'N1',
            version: 'runtime',
            status: 'ready',
            ingest_summary: { files_total: 6, chunks_total: 5 },
          },
        ],
      },
    })

    clientPostMock.mockResolvedValue({
      data: {
        draft_id: 'draft-runtime-001',
        project_id: 'project-fourier-n1',
        request_id: 'req-runtime-001',
        review_status: 'draft_pending_review',
        draft: {
          title: 'Fourier N1 肘关节维保',
          steps: [
            {
              step_id: 'step_001',
              title: '检查肘关节温度',
              description: '确认目标模组无异常温升',
              model_targets: ['elbow_joint'],
            },
          ],
          review_notes: ['part mapping requires review: elbow_joint'],
        },
        verdict_steps: [],
        viewer_manifest: {
          robotId: 'fourier-n1-runtime',
          label: 'Fourier N1',
          parts: ['viewer/elbow.glb'],
          assets: [
            {
              asset_id: 'elbow_joint::viewer/elbow.glb',
              asset_type: 'gltf',
              node_id: 'elbow_joint',
              path: 'viewer/elbow.glb',
              source_paths: ['viewer/elbow.glb'],
            },
          ],
          needs_review_nodes: ['elbow_joint'],
        },
        manifest_tree: {
          robot_key: 'fourier-n1-runtime',
          root_nodes: ['elbow_joint'],
          nodes: [
            {
              id: 'elbow_joint',
              display_name: 'elbow_joint',
              parent_id: null,
              children: [],
              source_paths: ['viewer/elbow.glb'],
              runtime_asset_paths: ['viewer/elbow.glb'],
              file_kinds: ['viewer_asset'],
            },
          ],
        },
        manifest_mapping: {
          elbow_joint: {
            source_paths: ['viewer/elbow.glb'],
            runtime_asset_paths: ['viewer/elbow.glb'],
            file_kinds: ['viewer_asset'],
          },
        },
        citations: [
          {
            title: '执行器维护说明',
            source: 'semantic',
          },
        ],
      },
    })
  })

  it('loads ready projects and generates runtime draft from the dedicated page', async () => {
    const user = userEvent.setup()

    render(<MaintenanceProjectDraftPage />)

    expect(screen.getByRole('heading', { name: '项目草案页' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '生成 AI 草案' })).toBeTruthy()

    await waitFor(() => {
      expect(clientGetMock).toHaveBeenCalled()
    })

    await user.click(screen.getByRole('button', { name: '生成 AI 草案' }))

    await waitFor(() => {
      expect(clientPostMock).toHaveBeenCalled()
    })

    expect(await screen.findByText('Fourier N1 肘关节维保')).toBeTruthy()
    expect(screen.getByRole('button', { name: '在 SOP 工作台打开' })).toBeTruthy()
  })
})
