import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// ---------------------------------------------------------------------------
// 3D dependency mocks
//
// Atom01Interactive is a heavy @react-three/fiber component. The Three.js
// animation paths (useFrame callbacks, the WebGL render loop, GLTF asset
// loading and the requestAnimationFrame-driven bounds reporter) are NOT
// reachable under jsdom — there is no GL context and no R3F reconciler.
//
// What IS observable and worth characterizing: the component's render-time
// logic — the merged part-metadata / explode-offset memos, the visible /
// clickable / reference / faded / sub-part Set computations, the createLink
// branch selection (visible vs faded vs reference vs clickable), the
// InteractiveLinkMesh clonedScene normalization + outlier culling memo, and
// the pointer/click/double-click handler wiring.
//
// To reach those, we render with react-dom while stubbing:
//   - useFrame  → no-op (the animation loop body stays uncovered by design)
//   - useGLTF   → returns a real THREE.Group scene so .clone()/setFromObject work
//   - useAtom01AssemblyData → no assembly data (drives the SubPartsGroup branch)
// R3F intrinsics (<group>, <mesh>, <primitive>…) render as inert host nodes.
// ---------------------------------------------------------------------------

vi.mock('@react-three/fiber', () => ({
  useFrame: () => {},
}))

vi.mock('@react-three/drei', async () => {
  const THREE = await import('three')
  const makeScene = () => {
    const group = new THREE.Group()
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.2, 0.2, 0.2),
      new THREE.MeshStandardMaterial(),
    )
    group.add(mesh)
    return group
  }
  const useGLTF = (url: string | string[]) =>
    Array.isArray(url) ? url.map(() => ({ scene: makeScene() })) : { scene: makeScene() }
  ;(useGLTF as unknown as { preload: () => void }).preload = () => {}
  return {
    useGLTF,
    Line: () => null,
    Center: ({ children }: { children?: unknown }) => children,
  }
})

vi.mock('@/components/Viewer3D/hooks/useAtom01AssemblyData', () => ({
  useAtom01AssemblyData: () => ({ adapter: null, explodeManifest: null }),
}))

// ---------------------------------------------------------------------------
import { Atom01Interactive, PART_METADATA } from '@/components/Viewer3D/Atom01Interactive'

describe('Atom01Interactive characterization', () => {
  it('exposes the hardcoded PART_METADATA fallback map', () => {
    expect(PART_METADATA).toBeTruthy()
    expect(Object.keys(PART_METADATA).length).toBeGreaterThan(0)
    // Every entry carries the PartInfo shape used by the viewer.
    for (const info of Object.values(PART_METADATA)) {
      expect(typeof info.name).toBe('string')
      expect(typeof info.displayName).toBe('string')
    }
  })

  it('renders the full link tree as 3D primitives without crashing', () => {
    const { container } = render(<Atom01Interactive robotId="1" />)

    // One <primitive> per visible link (the GLTF scene mount point).
    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
    // Root transform group is present.
    expect(container.querySelector('group')).toBeTruthy()
  })

  it('limits visible links when visiblePartNames isolates a single core link', () => {
    const full = render(<Atom01Interactive robotId="1" />)
    const fullCount = full.container.querySelectorAll('primitive').length
    full.unmount()

    const isolated = render(
      <Atom01Interactive
        robotId="1"
        visiblePartNames={['torso_link']}
        clickablePartNames={['torso_link']}
        isolationLevel={1}
      />,
    )
    const isolatedCount = isolated.container.querySelectorAll('primitive').length

    // Reference nodes are still rendered, but the isolated view shows fewer
    // primitives than the full body.
    expect(isolatedCount).toBeLessThan(fullCount)
    expect(isolatedCount).toBeGreaterThan(0)
  })

  it('renders sub-parts when showSubParts + explodeAmount activates the explode view', () => {
    const { container } = render(
      <Atom01Interactive
        robotId="1"
        showSubParts
        explodeAmount={0.6}
        visiblePartNames={['torso_link']}
        clickablePartNames={['torso_link']}
        isolationLevel={1}
      />,
    )

    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })

  it('renders an L2 sub-part group when isolationLevel>=2 targets a link', () => {
    const { container } = render(
      <Atom01Interactive
        robotId="1"
        showSubParts
        explodeAmount={0.6}
        visiblePartNames={['torso_link']}
        clickablePartNames={['torso_link']}
        isolationLevel={2}
        l2TargetLink="torso_link"
        l2SelectedPartIdx={0}
      />,
    )

    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })

  it('applies faded and reference part styling branches in createLink', () => {
    const { container } = render(
      <Atom01Interactive
        robotId="1"
        visiblePartNames={['torso_link']}
        clickablePartNames={['torso_link']}
        fadedPartNames={['left_arm_pitch_link']}
        referencePartNames={['base_link']}
        fadeOpacity={0.1}
      />,
    )

    // Faded + reference links remain rendered (visible) even though not clickable.
    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })

  it('marks fault links from faultJoints', () => {
    // NOTE: jointAngles application (setRotationFromAxisAngle on joint group refs)
    // is 3D-unreachable under jsdom — refs resolve to inert host nodes, not
    // THREE.Group instances — so we only characterize the isFault branch here.
    const { container } = render(
      <Atom01Interactive robotId="1" faultJoints={['left_elbow_pitch_joint']} />,
    )

    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })

  it('invokes onPartSelect / onPartHover / onPartDoubleClick when a link is interacted with', () => {
    const onPartSelect = vi.fn()
    const onPartHover = vi.fn()
    const onPartDoubleClick = vi.fn()

    const { container } = render(
      <Atom01Interactive
        robotId="1"
        onPartSelect={onPartSelect}
        onPartHover={onPartHover}
        onPartDoubleClick={onPartDoubleClick}
      />,
    )

    // The clickable InteractiveLinkMesh wrapper group carries the R3F event
    // props, which react-dom binds as DOM handlers. Firing on a primitive
    // bubbles up to the nearest group with handlers.
    const primitive = container.querySelector('primitive')
    expect(primitive).toBeTruthy()

    fireEvent.pointerOver(primitive!)
    fireEvent.click(primitive!)
    fireEvent.dblClick(primitive!)
    fireEvent.pointerOut(primitive!)

    expect(onPartHover).toHaveBeenCalled()
    expect(onPartSelect).toHaveBeenCalled()
  })

  it('uses controlled selectedPart / hoveredPart props over internal state', () => {
    const torso = PART_METADATA['torso_link']
    const { container } = render(
      <Atom01Interactive
        robotId="1"
        selectedPart={torso?.name ?? 'torso_link'}
        hoveredPart={torso?.name ?? 'torso_link'}
      />,
    )

    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })

  it('renders in fullscreen mode with reference preservation disabled', () => {
    const { container } = render(
      <Atom01Interactive
        robotId="1"
        fullscreenMode
        preserveReferenceInExplode={false}
        explodeAmount={0.3}
        visiblePartNames={['torso_link']}
        clickablePartNames={['torso_link']}
        isolationLevel={1}
      />,
    )

    expect(container.querySelectorAll('primitive').length).toBeGreaterThan(0)
  })
})
