import { BatteryStorage } from '@/features/site/components/BatteryStorage'
import { ChargingStation } from '@/features/site/components/ChargingStation'
import { ParkedVehicle } from '@/features/site/components/ParkedVehicle'
import { SceneCamera } from '@/features/site/components/SceneCamera'
import { SolarCanopy } from '@/features/site/components/SolarCanopy'
import type { SiteView } from '@/features/site/scene-model'
import { CHARGER_X_POSITIONS } from '@/features/site/scene-model'
import { type Wallbox } from '@/shared/api/contracts/charging'
import { Canvas } from '@react-three/fiber'

export function MicrogridScene({
  boxes,
  solar,
  soc,
  view,
  choose,
  xray,
}: {
  boxes: Wallbox[]
  solar: number | null
  soc: number | null
  view: SiteView
  choose: (view: SiteView) => void
  xray: boolean
}) {
  return (
    <Canvas
      shadows
      dpr={[1, 1.6]}
      camera={{ position: [30, 27, 33], fov: 42, near: 0.1, far: 180 }}
      gl={{ antialias: true, alpha: true }}
    >
      <color attach="background" args={['#141413']} />
      <fog attach="fog" args={['#141413', 52, 120]} />
      <ambientLight intensity={1.15} color="#b7d6dc" />
      <hemisphereLight intensity={1.2} color="#b4e1e6" groundColor="#12252f" />
      <directionalLight
        position={[-16, 27, 18]}
        intensity={3.2}
        color="#e5f9ff"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-42}
        shadow-camera-right={42}
        shadow-camera-top={34}
        shadow-camera-bottom={-34}
      />
      <pointLight position={[3, 12, -10]} intensity={18} color="#8faf86" distance={45} />
      <mesh position={[0, -0.35, 0]} receiveShadow>
        <boxGeometry args={[48, 0.7, 31]} />
        <meshStandardMaterial color="#14232c" roughness={0.9} />
      </mesh>
      <mesh position={[0, -0.035, 0]} receiveShadow>
        <boxGeometry args={[47.6, 0.06, 30.6]} />
        <meshStandardMaterial color="#24353e" roughness={0.95} />
      </mesh>
      {[-14, -7, 0, 7, 14].map((z) => (
        <mesh key={z} position={[-1, 0.006, z]}>
          <boxGeometry args={[36, 0.012, 0.035]} />
          <meshBasicMaterial color="#81989b" transparent opacity={0.34} />
        </mesh>
      ))}
      {CHARGER_X_POSITIONS.map((x) => (
        <group key={x}>
          {[-7, 7].map((z) => (
            <group key={z}>
              <mesh position={[x - 3.35, 0.016, z]}>
                <boxGeometry args={[0.045, 0.014, 7.2]} />
                <meshBasicMaterial color="#bdcbc6" transparent opacity={0.72} />
              </mesh>
              <mesh position={[x, 0.09, z < 0 ? -11.1 : 11.1]}>
                <boxGeometry args={[2.3, 0.16, 0.24]} />
                <meshStandardMaterial color="#aabbbc" />
              </mesh>
            </group>
          ))}
        </group>
      ))}
      <SolarCanopy z={-7} solar={solar} ghost={false} />
      <SolarCanopy z={7} solar={solar} ghost={xray} />
      {boxes.map((box, i) => (
        <ChargingStation
          key={box.id}
          box={box}
          index={i}
          chosen={view === box.id}
          choose={choose}
        />
      ))}
      {boxes.map((box, i) =>
        box.power_kw != null && box.power_kw > 0.25 ? (
          <ParkedVehicle key={box.id} x={CHARGER_X_POSITIONS[i % 4]} z={i < 4 ? -7.3 : 7.3} />
        ) : null,
      )}
      <BatteryStorage soc={soc} chosen={view === 'battery'} choose={() => choose('battery')} />
      <mesh position={[-19.7, 1.25, 0]} castShadow>
        <boxGeometry args={[3.2, 2.5, 4]} />
        <meshStandardMaterial color="#6d858d" metalness={0.6} roughness={0.37} />
      </mesh>
      <mesh position={[-19.7, 2.54, 0]}>
        <boxGeometry args={[3.35, 0.12, 4.2]} />
        <meshStandardMaterial color="#344b54" metalness={0.55} />
      </mesh>
      <SceneCamera view={view} boxes={boxes} />
    </Canvas>
  )
}
