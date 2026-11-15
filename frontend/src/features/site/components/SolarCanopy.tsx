import { SITE_ACCENT_COLOR } from '@/features/site/scene-model'

export function SolarCanopy({
  z,
  solar,
  ghost,
}: {
  z: number
  solar: number | null
  ghost: boolean
}) {
  return (
    <group position={[0, 0, z]}>
      {[-15.7, -5.2, 5.2, 15.7].map((x) => (
        <group key={x}>
          <mesh position={[x, 2.5, z < 0 ? 3.5 : -3.5]} castShadow>
            <boxGeometry args={[0.22, 5, 0.22]} />
            <meshStandardMaterial color="#91a9ae" metalness={0.8} roughness={0.3} />
          </mesh>
          <mesh position={[x, 0.09, z < 0 ? 3.5 : -3.5]}>
            <boxGeometry args={[0.65, 0.18, 0.65]} />
            <meshStandardMaterial color="#62747a" />
          </mesh>
        </group>
      ))}
      <mesh position={[0, 5.05, 0]} castShadow={!ghost}>
        <boxGeometry args={[34.7, 0.17, 8.1]} />
        <meshStandardMaterial
          color="#3b5663"
          metalness={0.72}
          roughness={0.28}
          transparent={ghost}
          opacity={ghost ? 0.18 : 1}
          depthWrite={!ghost}
        />
      </mesh>
      {Array.from({ length: 12 }, (_, i) =>
        Array.from({ length: 3 }, (_, j) => (
          <group key={i + '-' + j} position={[-15.55 + i * 2.83, 5.17, -2.55 + j * 2.55]}>
            <mesh>
              <boxGeometry args={[2.67, 0.07, 2.35]} />
              <meshStandardMaterial
                color="#0b2332"
                metalness={0.54}
                roughness={0.23}
                emissive={solar != null && solar > 0.1 ? '#0a2d39' : '#000000'}
                emissiveIntensity={0.6}
                transparent={ghost}
                opacity={ghost ? 0.24 : 1}
                depthWrite={!ghost}
              />
            </mesh>
            <mesh position={[0, 0.039, 0]}>
              <boxGeometry args={[2.57, 0.006, 2.25]} />
              <meshStandardMaterial
                color="#16405a"
                metalness={0.7}
                roughness={0.2}
                transparent={ghost}
                opacity={ghost ? 0.24 : 1}
                depthWrite={!ghost}
              />
            </mesh>
            {[-0.6, 0, 0.6].map((dx) => (
              <mesh key={dx} position={[dx, 0.045, 0]}>
                <boxGeometry args={[0.012, 0.008, 2.17]} />
                <meshBasicMaterial
                  color="#6aa3ae"
                  transparent
                  opacity={ghost ? 0.18 : 0.55}
                  depthWrite={!ghost}
                />
              </mesh>
            ))}
          </group>
        )),
      )}
      <mesh position={[0, 4.93, z < 0 ? 4.02 : -4.02]}>
        <boxGeometry args={[34.4, 0.04, 0.04]} />
        <meshBasicMaterial color={solar != null && solar > 0.1 ? SITE_ACCENT_COLOR : '#4c7079'} />
      </mesh>
    </group>
  )
}
