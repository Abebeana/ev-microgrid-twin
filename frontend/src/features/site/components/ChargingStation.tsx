import { CHARGER_X_POSITIONS, SITE_ACCENT_COLOR, stateOf } from '@/features/site/scene-model'
import { type Wallbox } from '@/shared/api/contracts/charging'
import { Html, RoundedBox } from '@react-three/drei'
import { type ThreeEvent } from '@react-three/fiber'

export function ChargingStation({
  box,
  index,
  chosen,
  choose,
}: {
  box: Wallbox
  index: number
  chosen: boolean
  choose: (id: string) => void
}) {
  const x = CHARGER_X_POSITIONS[index % 4],
    z = index < 4 ? -3 : 3
  const state = stateOf(box)
  const color =
    state === 'fault'
      ? '#ff9d7e'
      : state === 'charging'
        ? SITE_ACCENT_COLOR
        : state === 'idle'
          ? '#b8e6ad'
          : '#7b929b'
  const click = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    choose(box.id)
  }
  return (
    <group
      position={[x, 0, z]}
      onClick={click}
      onPointerOver={() => {
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        document.body.style.cursor = ''
      }}
    >
      <mesh position={[0, 0.025, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.7, chosen ? 0.84 : 0.77, 48]} />
        <meshBasicMaterial color={color} transparent opacity={chosen ? 1 : 0.72} />
      </mesh>
      {chosen && (
        <mesh position={[0, 0.022, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[0.7, 48]} />
          <meshBasicMaterial color={color} transparent opacity={0.15} depthWrite={false} />
        </mesh>
      )}
      <RoundedBox
        args={[0.77, 2.15, 0.6]}
        radius={0.12}
        smoothness={3}
        position={[0, 1.16, 0]}
        castShadow
      >
        <meshPhysicalMaterial color="#d6e5e2" metalness={0.35} roughness={0.27} clearcoat={0.8} />
      </RoundedBox>
      <mesh position={[0, 1.58, index < 4 ? 0.311 : -0.311]}>
        <boxGeometry args={[0.44, 0.55, 0.024]} />
        <meshStandardMaterial color="#0b2531" emissive="#0b3440" emissiveIntensity={0.5} />
      </mesh>
      <mesh position={[0, 2.31, 0]}>
        <boxGeometry args={[0.56, 0.055, 0.47]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={chosen ? 1.3 : 0.7}
        />
      </mesh>
      <mesh position={[0.55, 0.6, 0]}>
        <torusGeometry args={[0.35, 0.03, 8, 24, Math.PI * 1.5]} />
        <meshStandardMaterial color="#172027" roughness={0.9} />
      </mesh>
      <mesh position={[0, 1.1, 0]}>
        <boxGeometry args={[1.7, 2.3, 1.7]} />
        <meshBasicMaterial visible={false} />
      </mesh>
      <Html position={[0, 2.86, 0]} center distanceFactor={17} style={{ pointerEvents: 'none' }}>
        <div className={'site-3d-label ' + (chosen ? 'selected ' : '') + state}>
          <i />
          {box.id}
          {chosen && <b>{box.power_kw == null ? '—' : box.power_kw.toFixed(2) + ' kW'}</b>}
        </div>
      </Html>
    </group>
  )
}
