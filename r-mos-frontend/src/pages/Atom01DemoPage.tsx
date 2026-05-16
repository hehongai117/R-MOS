import { UniversalRobotViewer } from '@/components/Viewer3D/UniversalRobotViewer'
import { useRobotContextStore } from '@/store/robotContextStore'

function Atom01DemoPage() {
  const currentRobot = useRobotContextStore((s) => s.currentRobot)

  if (!currentRobot) {
    return (
      <div style={{ height: 'calc(100vh - 6rem)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: '#999' }}>
          <p style={{ fontSize: '1.125rem' }}>请先选择一台机器人</p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#666' }}>
            在顶部导航栏中选择要查看的机器人型号
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ height: 'calc(100vh - 6rem)' }}>
      <UniversalRobotViewer
        robotId={currentRobot.id}
        robotName={`${currentRobot.brand} ${currentRobot.model_name}`}
      />
    </div>
  )
}

export default Atom01DemoPage
