"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * A quiet field of drifting points behind the hero — meant to read as
 * "ambient data," not as a centerpiece. This is the project's one
 * deliberate use of 3D: the brief asked for 3D only where it genuinely
 * adds value, and a data-analyst product's most honest visual metaphor
 * is scattered points slowly finding structure, not an object or logo.
 *
 * Kept intentionally dim (low opacity, slow drift, no bloom/glow) so it
 * never competes with the actual content in front of it, and is skipped
 * entirely under prefers-reduced-motion.
 */
function PointField() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const count = 700;
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 18;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 10;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 8;
    }
    return arr;
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;
    const t = state.clock.getElapsedTime();
    pointsRef.current.rotation.y = t * 0.012;
    pointsRef.current.rotation.x = Math.sin(t * 0.05) * 0.04;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.028}
        color="#E2A23B"
        transparent
        opacity={0.35}
        sizeAttenuation
      />
    </points>
  );
}

export function DataFieldCanvas() {
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (prefersReducedMotion) return null;

  return (
    <div
      className="pointer-events-none absolute inset-0 -z-10 opacity-70"
      aria-hidden="true"
    >
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }} dpr={[1, 1.5]}>
        <PointField />
      </Canvas>
    </div>
  );
}
