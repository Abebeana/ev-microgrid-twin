import { RoundedBox } from '@react-three/drei'

export function ParkedVehicle({ x, z }: { x: number; z: number }) {
  return (
    <group position={[x, 0, z]} rotation={[0, z > 0 ? Math.PI : 0, 0]}>
      <RoundedBox
        args={[2.25, 0.63, 3.85]}
        radius={0.26}
        smoothness={3}
        position={[0, 0.62, 0]}
        castShadow
      >
        <meshPhysicalMaterial color="#d9e9e7" metalness={0.55} roughness={0.25} clearcoat={0.8} />
      </RoundedBox>
      <RoundedBox
        args={[1.88, 0.7, 2.1]}
        radius={0.26}
        smoothness={3}
        position={[0, 1.13, 0.13]}
        castShadow
      >
        <meshPhysicalMaterial color="#c9d9d7" metalness={0.5} roughness={0.26} clearcoat={0.7} />
      </RoundedBox>
      <mesh position={[0, 1.17, -0.91]} rotation={[0.3, 0, 0]}>
        <boxGeometry args={[1.65, 0.025, 0.63]} />
        <meshStandardMaterial color="#122f3d" metalness={0.3} roughness={0.17} />
      </mesh>
      {[-1.04, 1.04].flatMap((sx) =>
        [-1.24, 1.24].map((sz) => (
          <mesh key={sx + '-' + sz} position={[sx, 0.4, sz]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.35, 0.35, 0.18, 16]} />
            <meshStandardMaterial color="#101a20" roughness={0.9} />
          </mesh>
        )),
      )}
      {[-0.72, 0.72].map((sx) => (
        <mesh key={sx} position={[sx, 0.62, -1.93]}>
          <boxGeometry args={[0.36, 0.1, 0.025]} />
          <meshBasicMaterial color="#d8fff4" />
        </mesh>
      ))}
    </group>
  )
}
