# Motor Gráfico Aeón (React Three Fiber) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a highly optimized, aesthetically unique 3D visual engine for the Aeon using React Three Fiber, featuring procedural particles and audio-reactivity.

**Architecture:** We will use `react-three-fiber` and `drei` to render a particle system. The particles will be positioned using a custom BufferGeometry to form an abstract humanoid/mythological shape. A custom GLSL ShaderMaterial will handle the visual styling (glow, color palettes based on the Aeon's DNA) and the audio-reactive deformation. We will integrate this into the existing `AeonAvatar.tsx` component in `aria-ui`.

**Tech Stack:** Next.js (React), React Three Fiber, Three.js, GLSL (Shaders).

---

### Task 1: Setup 3D Canvas Foundation

**Files:**
- Modify: `aria-ui/components/AeonAvatar.tsx`

- [ ] **Step 1: Replace placeholder with Canvas**
Modify `AeonAvatar.tsx` to mount a `Canvas` from `@react-three/fiber` instead of the current 2D gradient placeholder.

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

// Inside AeonAvatar component:
return (
  <div className="w-full h-full relative">
    <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
      <ambientLight intensity={0.5} />
      <OrbitControls enableZoom={false} enablePan={false} />
      {/* Aeon Entity will go here */}
    </Canvas>
  </div>
);
```

- [ ] **Step 2: Commit**
```bash
git add aria-ui/components/AeonAvatar.tsx
git commit -m "feat(ui): setup r3f canvas for aeon avatar"
```

### Task 2: Implement Procedural Particle Geometry

**Files:**
- Create: `aria-ui/components/AeonEntity.tsx`
- Modify: `aria-ui/components/AeonAvatar.tsx`

- [ ] **Step 1: Create AeonEntity component with BufferGeometry**
Generate points distributed in a sphere (as a starting base before humanoid mapping) using `useMemo`.

```tsx
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
    const palette = dna?.visual_genes?.color_palette || ['#4f46e5', '#8b5cf6'];
    const baseColor = new THREE.Color(palette[0]);
    const altColor = new THREE.Color(palette[1 % palette.length]);

    for (let i = 0; i < particleCount; i++) {
      // Golden ratio spiral distribution on a sphere
      const phi = Math.acos(1 - 2 * (i + 0.5) / particleCount);
      const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
      
      const r = 2.0; // Radius
      
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
```

- [ ] **Step 2: Add AeonEntity to Canvas**
Import and render `<AeonEntity dna={dna} />` inside the Canvas in `AeonAvatar.tsx`.

- [ ] **Step 3: Commit**
```bash
git add aria-ui/components/AeonEntity.tsx aria-ui/components/AeonAvatar.tsx
git commit -m "feat(ui): implement procedural particle geometry for aeon"
```

### Task 3: Implement Custom GLSL Shader for Audio Reactivity

**Files:**
- Modify: `aria-ui/components/AeonEntity.tsx`
- Modify: `aria-ui/lib/zana-stream.ts` (to expose audio level)

- [ ] **Step 1: Expose audio activity from stream**
In `zana-stream.ts`, add a `currentAudioLevel` state (mocked for now, to be linked to actual audio context later).
```typescript
  const [audioLevel, setAudioLevel] = useState(0);
  // Export audioLevel in the returned object
```

- [ ] **Step 2: Create ShaderMaterial**
Replace `pointsMaterial` with a `shaderMaterial` in `AeonEntity.tsx` that accepts a `uAudioLevel` uniform.

```tsx
import { shaderMaterial } from '@react-three/drei';
import { extend } from '@react-three/fiber';

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
    pos += normal * noise * uAudioLevel * 0.5; 
    
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

// Update JSX:
// <aeonShaderMaterial attach="material" transparent depthWrite={false} blending={THREE.AdditiveBlending} />

// Update useFrame:
// materialRef.current.uTime = state.clock.elapsedTime;
// materialRef.current.uAudioLevel = THREE.MathUtils.lerp(materialRef.current.uAudioLevel, targetAudioLevel, 0.1);
```

- [ ] **Step 3: Commit**
```bash
git add aria-ui/components/AeonEntity.tsx aria-ui/lib/zana-stream.ts
git commit -m "feat(ui): add glsl shader for audio reactivity"
```
