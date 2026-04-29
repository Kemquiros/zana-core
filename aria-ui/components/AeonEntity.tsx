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
    const geomType = dna?.geometry_type || 'fluid';

    for (let i = 0; i < particleCount; i++) {
      let x, y, z;

      if (geomType === 'geometric') {
        // Cube distribution
        x = (Math.random() - 0.5) * 2.5;
        y = (Math.random() - 0.5) * 2.5;
        z = (Math.random() - 0.5) * 2.5;
      } else if (geomType === 'crystal') {
        // Diamond/Octahedron distribution
        const u = Math.random() * 2 - 1;
        const v = Math.random() * 2 - 1;
        const w = Math.random() * 2 - 1;
        const sum = Math.abs(u) + Math.abs(v) + Math.abs(w);
        x = u / sum * 1.8;
        y = v / sum * 1.8;
        z = w / sum * 1.8;
      } else if (geomType === 'ethereal') {
        // Torus distribution (Ring/Angel-like)
        const R = 1.3;
        const r_torus = 0.4;
        const u = Math.random() * Math.PI * 2;
        const v = Math.random() * Math.PI * 2;
        x = (R + r_torus * Math.cos(v)) * Math.cos(u);
        y = (R + r_torus * Math.cos(v)) * Math.sin(u);
        z = r_torus * Math.sin(v);
      } else if (geomType === 'organic') {
        // Humanoid/Beast-like (Two-lobe distribution)
        if (i < particleCount * 0.7) {
          // Body
          const phi = Math.acos(1 - 2 * (i + 0.5) / (particleCount * 0.7));
          const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
          x = 0.8 * Math.cos(theta) * Math.sin(phi);
          y = 1.2 * Math.sin(theta) * Math.sin(phi) - 0.4;
          z = 0.8 * Math.cos(phi);
        } else {
          // Head
          const headIdx = i - particleCount * 0.7;
          const phi = Math.acos(1 - 2 * (headIdx + 0.5) / (particleCount * 0.3));
          const theta = Math.PI * (1 + Math.sqrt(5)) * (headIdx + 0.5);
          x = 0.5 * Math.cos(theta) * Math.sin(phi);
          y = 0.5 * Math.sin(theta) * Math.sin(phi) + 0.7;
          z = 0.5 * Math.cos(phi);
        }
      } else {
        // Default Fluid Sphere (Golden Spiral)
        const phi = Math.acos(1 - 2 * (i + 0.5) / particleCount);
        const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
        x = 1.5 * Math.cos(theta) * Math.sin(phi);
        y = 1.5 * Math.sin(theta) * Math.sin(phi);
        z = 1.5 * Math.cos(phi);
      }
      
      pos[i * 3] = x;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = z;

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
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      {/* @ts-expect-error - Custom element extended dynamically */}
      <aeonShaderMaterial ref={materialRef} attach="material" transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}