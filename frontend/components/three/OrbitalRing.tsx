"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface OrbitalRingProps {
  radius?: number;
  tilt?: number;
  rotationSpeed?: number;
  color?: string;
  opacity?: number;
}

export default function OrbitalRing({
  radius = 5,
  tilt = 0.3,
  rotationSpeed = 0.08,
  color = "#00c8ff",
  opacity = 0.15,
}: OrbitalRingProps) {
  const ref = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * rotationSpeed;
    }
  });

  return (
    <group ref={ref} rotation={[tilt, 0, 0]}>
      <mesh>
        <torusGeometry args={[radius, 0.008, 16, 128]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={opacity}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      {/* Faint outer glow ring */}
      <mesh>
        <torusGeometry args={[radius, 0.04, 8, 128]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={opacity * 0.25}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
