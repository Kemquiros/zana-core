'use client';

import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { extend, useFrame } from '@react-three/fiber';
import { shaderMaterial } from '@react-three/drei';

const AeonShaderMaterial = shaderMaterial(
  { uTime: 0, uAudioLevel: 0 },
  // Vertex Shader
  `
  uniform float uTime;
  uniform float uAudioLevel;
  attribute vec3 color;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec3 pos = position;
    // Audio reactive expansion
    float noise = sin(pos.x * 5.0 + uTime) * cos(pos.y * 5.0 + uTime);
    // Approximate normal by normalizing position since it's a sphere
    vec3 norm = normalize(pos);
    pos += norm * noise * uAudioLevel * 0.5; 
    
    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = (10.0 + uAudioLevel * 20.0) * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
  `,
  // Fragment Shader
  `
  varying vec3 vColor;
  void main() {
    // Soft circular particle
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;
    float alpha = smoothstep(0.5, 0.1, dist);
    gl_FragColor = vec4(vColor, alpha * 0.8);
  }
  `
);

extend({ AeonShaderMaterial });

export default function AeonEntity({ dna, audioLevel = 0 }: { dna: any, audioLevel?: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<any>(null);
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
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime;
      materialRef.current.uAudioLevel = THREE.MathUtils.lerp(materialRef.current.uAudioLevel, audioLevel, 0.1);
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={particleCount} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={particleCount} array={colors} itemSize={3} />
      </bufferGeometry>
      {/* @ts-expect-error - Custom element extended dynamically */}
      <aeonShaderMaterial ref={materialRef} attach="material" transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}