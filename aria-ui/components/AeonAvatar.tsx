'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Stars, MeshTransmissionMaterial, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import { AeonVisualDNA } from '../lib/koru-types';

function GenerativeCore({ dna }: { dna: AeonVisualDNA | null }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const groupRef = useRef<THREE.Group>(null!);
  
  const primaryColor = dna?.chroma_spectrum?.[0] ?? '#4F46E5';
  const secondaryColor = dna?.chroma_spectrum?.[1] ?? '#1E1B4B';
  const mutation = dna?.mutation_factor ?? 0.5;
  const pulseSpeed = dna?.vibration_frequency ?? 1.5;
  const modelIndex = dna?.base_model_index ?? 0;
  const geomType = dna?.geometry_type ?? 'fluid';

  // Memoize geometry to avoid expensive recalculations
  const geometry = useMemo(() => {
    // Select base geometry based on model index and type
    if (geomType === 'geometric') {
        return modelIndex % 2 === 0 ? new THREE.BoxGeometry(1.2, 1.2, 1.2) : new THREE.TetrahedronGeometry(1.4);
    } else if (geomType === 'crystal') {
        return new THREE.OctahedronGeometry(1.2, 0);
    } else if (geomType === 'organic') {
        return new THREE.IcosahedronGeometry(1.1, 1);
    } else if (geomType === 'ethereal') {
        return new THREE.TorusKnotGeometry(0.6, 0.2, 128, 16);
    }
    return new THREE.SphereGeometry(1, 64, 64);
  }, [geomType, modelIndex]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
        meshRef.current.rotation.y = t * 0.2 * (1 + mutation);
        meshRef.current.rotation.z = t * 0.1 * mutation;
        
        // Tamagotchi-style "life" vibration
        const scaleVal = 1 + Math.sin(t * pulseSpeed) * 0.05;
        meshRef.current.scale.setScalar(scaleVal * (dna?.scale ?? 1));
        
        // Vertex jitter simulation via group rotation
        if (groupRef.current) {
            groupRef.current.rotation.x = Math.sin(t * 0.5) * 0.1 * mutation;
        }
    }
  });

  return (
    <group ref={groupRef}>
      <Float speed={2} rotationIntensity={0.5 * mutation} floatIntensity={1}>
        <mesh ref={meshRef} geometry={geometry}>
          <MeshTransmissionMaterial
            backside
            samples={4}
            thickness={0.5}
            roughness={0.1 * (1 - mutation)}
            transmission={1}
            ior={1.2 + mutation * 0.2}
            chromaticAberration={0.06 * mutation}
            color={primaryColor}
            emissive={secondaryColor}
            emissiveIntensity={0.3}
          />
        </mesh>
      </Float>
    </group>
  );
}

export default function AeonAvatar({ dna }: { dna: Record<string, unknown> | null }) {
  // If dna is actually the full profile, extract visual_dna
  const visualDna: AeonVisualDNA | null = (dna?.visual_dna as AeonVisualDNA) || (dna?.visual_genes ? {
    base_model_index: 0,
    mutation_factor: 0.5,
    chroma_spectrum: (dna.visual_genes as Record<string, unknown>).color_palette as string[],
    vibration_frequency: (dna.visual_genes as Record<string, unknown>).pulse_speed === 'intense' ? 3 : (dna.visual_genes as Record<string, unknown>).pulse_speed === 'calm' ? 0.5 : 1.5,
    particle_density: 1000,
    scale: 1,
    geometry_type: ((dna.visual_genes as Record<string, unknown>).particle_shape as string) || 'fluid'
  } as AeonVisualDNA : null);

  return (
    <div className="w-full h-full min-h-[400px]">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1.5} />
        <Stars radius={100} depth={50} count={visualDna?.particle_density ?? 5000} factor={4} saturation={0} fade speed={1} />
        
        <AeonEntity dna={visualDna} />
        
        {/* Dynamic Orbital rings based on base_model_index */}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[2, 0.01, 16, 100]} />
          <meshBasicMaterial color={visualDna?.chroma_spectrum?.[0] ?? '#4F46E5'} transparent opacity={0.2} />
        </mesh>

        {visualDna && visualDna.base_model_index % 2 === 0 && (
          <mesh rotation={[0, Math.PI / 2, 0]}>
            <torusGeometry args={[2.2, 0.005, 16, 100]} />
            <meshBasicMaterial color={visualDna.chroma_spectrum?.[1] ?? '#8B5CF6'} transparent opacity={0.1} />
          </mesh>
        )}

        <ContactShadows position={[0, -2, 0]} opacity={0.4} scale={10} blur={2} far={4.5} />
      </Canvas>
    </div>
  );
}
{4.5} />
      </Canvas>
    </div>
  );
}
