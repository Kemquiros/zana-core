'use client';

import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

export default function AeonEntity({ dna }: { dna: any }) {
  const pointsRef = useRef<THREE.Points>(null);
  const particleCount = 5000;

  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    const col = new Float32Array(particleCount * 3);
    const color = new THREE.Color();
    
    // Parse DNA colors
    const palette = dna?.chroma_spectrum || ['#4f46e5', '#8b5cf6'];
    const baseColor = new THREE.Color(palette[0]);
    const altColor = new THREE.Color(palette[1 % palette.length]);

    for (let i = 0; i < particleCount; i++) {
      // Golden ratio spiral distribution on a sphere
      const phi = Math.acos(1 - 2 * (i + 0.5) / particleCount);
      const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
      
      const r = 1.5; // Radius
      
      pos[i * 3] = r * Math.cos(theta) * Math.sin(phi);
      pos[i * 3 + 1] = r * Math.sin(theta) * Math.sin(phi);
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Mix colors based on position
      color.lerpColors(baseColor, altColor, Math.random());
      col[i * 3] = color.r;
      col[i * 3 + 1] = color.g;
      col[i * 3 + 2] = color.b;
    }
    return [pos, col];
  }, [dna, particleCount]);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.1;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={particleCount} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={particleCount} array={colors} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.05} vertexColors transparent opacity={0.8} blending={THREE.AdditiveBlending} depthWrite={false} />
    </points>
  );
}