import { SITE_ACCENT_COLOR } from '@/features/site/scene-model'
import { Html, RoundedBox } from '@react-three/drei'

export function BatteryStorage({
  soc,
  chosen,
  choose,
}: {
  soc: number | null
  chosen: boolean
  choose: () => void
}) {
  const fill = Math.max(0, Math.min(100, soc ?? 0)) / 100
  return (
    <group
      position={[19.5, 0, 0]}
      onClick={(event) => {
        event.stopPropagation()
        choose()
      }}
      onPointerOver={() => {
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        document.body.style.cursor = ''
      }}
    >
      <mesh position={[0, 0.14, 0]}>
        <boxGeometry args={[4.3, 0.28, 4.8]} />
        <meshStandardMaterial color="#60747b" />
      </mesh>
      <RoundedBox
        args={[3.7, 3.5, 3.9]}
        radius={0.14}
        smoothness={3}
        position={[0, 2.04, 0]}
        castShadow
      >
        <meshPhysicalMaterial color="#cbdad8" metalness={0.45} roughness={0.32} />
      </RoundedBox>
      {[-0.86, 0.86].map((x) => (
        <mesh key={x} position={[x, 2, 1.985]}>
          <boxGeometry args={[1.55, 3.06, 0.035]} />
          <meshStandardMaterial color="#8fa8ad" metalness={0.6} roughness={0.34} />
        </mesh>
      ))}
      <mesh position={[0, 3.56, 2.01]}>
        <boxGeometry args={[2.7, 0.13, 0.04]} />
        <meshBasicMaterial color="#1b343d" />
      </mesh>
      <mesh position={[-1.35 + 1.35 * fill, 3.56, 2.04]}>
        <boxGeometry args={[Math.max(0.01, 2.7 * fill), 0.13, 0.04]} />
        <meshBasicMaterial color={SITE_ACCENT_COLOR} />
      </mesh>
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[4.3, 4, 4.5]} />
        <meshBasicMaterial visible={false} />
      </mesh>
      <Html position={[0, 4.52, 0]} center distanceFactor={18} style={{ pointerEvents: 'none' }}>
        <div className={'site-3d-label ' + (chosen ? 'selected' : '')}>
          BESS <b>{soc == null ? '—' : soc.toFixed(1) + '%'}</b>
        </div>
      </Html>
    </group>
  )
}
