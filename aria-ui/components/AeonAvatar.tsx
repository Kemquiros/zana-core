'use client';

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Stars, MeshTransmissionMaterial } from '@react-three/drei';
import * as THREE from 'three';

interface AeonDNA {
  visual_genes: {
    color_palette: string[];
    particle_shape: string;
    pulse_speed: string;
  };
}

function AeonCore({ dna }: { dna: AeonDNA | null }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  
  const primaryColor = dna?.visual_genes?.color_palette?.[0] ?? '#4F46E5';
  const shape = dna?.visual_genes?.particle_shape ?? 'fluid';
  const pulseSpeed = dna?.visual_genes?.pulse_speed === 'intense' ? 3 : dna?.visual_genes?.pulse_speed === 'calm' ? 0.5 : 1.5;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
        meshRef.current.rotation.y = t * 0.2;
        meshRef.current.scale.setScalar(1 + Math.sin(t * pulseSpeed) * 0.05);
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <mesh ref={meshRef}>
        {shape === 'geometric' ? (
          <boxGeometry args={[1.2, 1.2, 1.2]} />
        ) : shape === 'crystal' ? (
          <octahedronGeometry args={[1.2, 0]} />
        ) : (
          <sphereGeometry args={[1, 64, 64]} />
        )}
        <MeshTransmissionMaterial
          backside
          samples={4}
          thickness={0.5}
          roughness={0.1}
          transmission={1}
          ior={1.2}
          chromaticAberration={0.06}
          color={primaryColor}
          emissive={primaryColor}
          emissiveIntensity={0.3}
        />
      </mesh>
    </Float>
  );
}

export default function AeonAvatar({ dna }: { dna: AeonDNA | null }) {
  return (
    <div className="w-full h-full min-h-[400px]">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1.5} />
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        
        <AeonCore dna={dna} />
        
        {/* Orbital ring */}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[2, 0.01, 16, 100]} />
          <meshBasicMaterial color={dna?.visual_genes?.color_palette?.[0] ?? '#4F46E5'} transparent opacity={0.2} />
        </mesh>
      </Canvas>
    </div>
  );
}
