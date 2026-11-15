import type { SiteView } from '@/features/site/scene-model'
import { positionFor } from '@/features/site/scene-model'
import { type Wallbox } from '@/shared/api/contracts/charging'
import { OrbitControls } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import { useEffect } from 'react'

export function SceneCamera({ view, boxes }: { view: SiteView; boxes: Wallbox[] }) {
  const { camera } = useThree()
  const target = positionFor(view, boxes)
  const [targetX, targetY, targetZ] = target
  useEffect(() => {
    const i = boxes.findIndex((box) => box.id === view)
    const pos =
      i >= 0
        ? [targetX + 8, 8, targetZ + 10]
        : view === 'solar'
          ? [15, 17, 10]
          : view === 'battery'
            ? [28, 10, 15]
            : [30, 27, 33]
    camera.position.set(pos[0], pos[1], pos[2])
    camera.lookAt(targetX, targetY, targetZ)
    camera.updateProjectionMatrix()
  }, [camera, view, boxes, targetX, targetY, targetZ])
  return (
    <OrbitControls
      key={view}
      target={target}
      enableDamping
      minDistance={7}
      maxDistance={82}
      maxPolarAngle={Math.PI * 0.48}
    />
  )
}
