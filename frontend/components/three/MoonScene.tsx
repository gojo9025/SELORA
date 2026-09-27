"use client";

import { useRef, Suspense, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import Starfield from "./Starfield";
import OrbitalRing from "./OrbitalRing";

/* ── Procedural Moon Material (no external textures needed) ── */
function useProceduralMoonTexture() {
  return useMemo(() => {
    const size = 1024;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;

    // Base grey
    ctx.fillStyle = "#8a8a8a";
    ctx.fillRect(0, 0, size, size);

    // Generate craters and surface detail
    const rng = (seed: number) => {
      let s = seed;
      return () => {
        s = (s * 16807) % 2147483647;
        return (s - 1) / 2147483646;
      };
    };
    const rand = rng(42);

    // Large maria (dark patches)
    for (let i = 0; i < 12; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 40 + rand() * 180;
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
      gradient.addColorStop(0, `rgba(60, 60, 65, ${0.3 + rand() * 0.3})`);
      gradient.addColorStop(0.7, `rgba(70, 70, 75, ${0.1 + rand() * 0.2})`);
      gradient.addColorStop(1, "rgba(100, 100, 100, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, size, size);
    }

    // Medium craters
    for (let i = 0; i < 200; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 3 + rand() * 25;
      const brightness = 60 + rand() * 50;

      // Shadow side
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${brightness - 20}, ${brightness - 20}, ${brightness - 15}, ${0.3 + rand() * 0.4})`;
      ctx.fill();

      // Bright rim
      ctx.beginPath();
      ctx.arc(x - r * 0.15, y - r * 0.15, r * 0.85, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${brightness + 30}, ${brightness + 30}, ${brightness + 25}, ${0.2 + rand() * 0.3})`;
      ctx.fill();

      // Center
      ctx.beginPath();
      ctx.arc(x, y, r * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${brightness - 10}, ${brightness - 10}, ${brightness - 5}, ${0.3 + rand() * 0.3})`;
      ctx.fill();
    }

    // Small craters / texture noise
    for (let i = 0; i < 3000; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 0.5 + rand() * 4;
      const brightness = 50 + rand() * 80;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${brightness}, ${brightness}, ${brightness}, ${0.15 + rand() * 0.25})`;
      ctx.fill();
    }

    // Highlands (bright areas)
    for (let i = 0; i < 8; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 60 + rand() * 140;
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
      gradient.addColorStop(0, `rgba(160, 160, 155, ${0.15 + rand() * 0.15})`);
      gradient.addColorStop(1, "rgba(130, 130, 130, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, size, size);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }, []);
}

function useProceduralBumpTexture() {
  return useMemo(() => {
    const size = 512;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;

    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, size, size);

    const rng = (seed: number) => {
      let s = seed;
      return () => {
        s = (s * 16807) % 2147483647;
        return (s - 1) / 2147483646;
      };
    };
    const rand = rng(123);

    // Crater depressions for bump map
    for (let i = 0; i < 300; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 2 + rand() * 18;
      const depth = 40 + rand() * 60;

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
      gradient.addColorStop(0, `rgb(${128 - depth}, ${128 - depth}, ${128 - depth})`);
      gradient.addColorStop(0.7, `rgb(${128 - depth / 3}, ${128 - depth / 3}, ${128 - depth / 3})`);
      gradient.addColorStop(1, "rgb(128, 128, 128)");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Fine noise
    for (let i = 0; i < 5000; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const v = 100 + rand() * 56;
      ctx.fillStyle = `rgb(${v}, ${v}, ${v})`;
      ctx.fillRect(x, y, 1, 1);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    return texture;
  }, []);
}

/* ── Moon Sphere ── */
function Moon() {
  const meshRef = useRef<THREE.Mesh>(null!);
  const groupRef = useRef<THREE.Group>(null!);

  const colorMap = useProceduralMoonTexture();
  const bumpMap = useProceduralBumpTexture();

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.06;
    }
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.15;
    }
  });

  return (
    <group ref={groupRef} position={[1.8, 0.2, 0]}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[2.2, 128, 128]} />
        <meshStandardMaterial
          map={colorMap}
          bumpMap={bumpMap}
          bumpScale={0.04}
          roughness={0.92}
          metalness={0.05}
          emissive="#0a1020"
          emissiveIntensity={0.08}
        />
      </mesh>
      {/* Atmospheric glow */}
      <mesh scale={1.04}>
        <sphereGeometry args={[2.2, 64, 64]} />
        <meshBasicMaterial
          color="#1a3a5c"
          transparent
          opacity={0.08}
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      {/* Limb glow */}
      <mesh scale={1.08}>
        <sphereGeometry args={[2.2, 64, 64]} />
        <meshBasicMaterial
          color="#0066aa"
          transparent
          opacity={0.04}
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

/* ── Tiny satellite dot orbiting the Moon ── */
function SatelliteDot() {
  const ref = useRef<THREE.Mesh>(null!);
  const trailRef = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    const t = state.clock.elapsedTime * 0.4;
    const x = 1.8 + Math.cos(t) * 3.2;
    const z = Math.sin(t) * 3.2;
    const y = 0.2 + Math.sin(t * 1.3) * 0.5;
    ref.current.position.set(x, y, z);

    // Trail follows slightly behind
    const tt = t - 0.15;
    trailRef.current.position.set(
      1.8 + Math.cos(tt) * 3.2,
      0.2 + Math.sin(tt * 1.3) * 0.5,
      Math.sin(tt) * 3.2
    );
  });

  return (
    <>
      <mesh ref={ref}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color="#00c8ff" />
      </mesh>
      <mesh ref={trailRef}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color="#00c8ff" transparent opacity={0.4} />
      </mesh>
    </>
  );
}

/* ── Main Scene ── */
export default function MoonScene() {
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 7], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{
          antialias: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        style={{ background: "transparent" }}
      >
        {/* Lighting */}
        <ambientLight intensity={0.1} color="#4a6b8a" />
        <directionalLight
          position={[-8, 3, 5]}
          intensity={2.0}
          color="#fff5e6"
        />
        <pointLight position={[10, 5, 10]} intensity={0.3} color="#00c8ff" />

        {/* Stars */}
        <Starfield count={4000} />

        {/* Moon */}
        <Moon />

        {/* Orbital Rings */}
        <group position={[1.8, 0.2, 0]}>
          <OrbitalRing radius={3.2} tilt={0.25} rotationSpeed={0.06} color="#00c8ff" opacity={0.12} />
          <OrbitalRing radius={3.8} tilt={-0.4} rotationSpeed={-0.03} color="#6366f1" opacity={0.08} />
          <OrbitalRing radius={4.5} tilt={0.6} rotationSpeed={0.02} color="#00c8ff" opacity={0.05} />
        </group>

        {/* Satellite */}
        <SatelliteDot />
      </Canvas>
    </div>
  );
}
