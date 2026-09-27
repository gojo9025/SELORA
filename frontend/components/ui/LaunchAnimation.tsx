"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LaunchAnimationProps {
  onComplete: () => void;
}

interface DataParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  alpha: number;
  decay: number;
  type: "dot" | "cross" | "coord" | "bit";
  text?: string;
  angle: number;
  vRot: number;
}

interface Keypoint {
  u: number;
  v: number;
  label: string;
  score: string;
  pairU: number;
  pairV: number;
}

export default function LaunchAnimation({ onComplete }: LaunchAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDismissing, setIsDismissing] = useState(false);
  const animFrameRef = useRef<number>(0);
  const hasCompletedRef = useRef<boolean>(false);

  const handleFinish = useCallback(() => {
    if (hasCompletedRef.current) return;
    hasCompletedRef.current = true;
    setIsDismissing(true);
    setTimeout(() => {
      onComplete();
    }, 450);
  }, [onComplete]);

  useEffect(() => {
    // Check prefers-reduced-motion
    if (typeof window !== "undefined") {
      const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
      if (mediaQuery.matches) {
        onComplete();
        return;
      }
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    // ── 1. BACKGROUND STARS (Subtle, realistic, high depth) ──
    const starCount = 350;
    const stars = Array.from({ length: starCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() < 0.85 ? Math.random() * 0.9 + 0.3 : Math.random() * 1.5 + 0.8,
      baseAlpha: Math.random() * 0.5 + 0.15,
      pulseSpeed: Math.random() * 0.02 + 0.005,
      pulseOffset: Math.random() * Math.PI * 2,
    }));

    // ── 2. LUNAR CRATER MAP (Procedural 3D Orthographic projection) ──
    const mapWidth = 800;
    const mapHeight = 400;

    let seed = 1337;
    const rnd = () => {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };

    // Basaltic Maria (dark volcanic plains: Imbrium, Serenitatis, Tranquillitatis, Oceanus Procellarum)
    const maria: Array<{ x: number; y: number; rx: number; ry: number; color: string }> = [
      { x: 260, y: 160, rx: 75, ry: 60, color: "rgba(38, 41, 48, 0.65)" }, // Oceanus Procellarum
      { x: 380, y: 130, rx: 65, ry: 50, color: "rgba(35, 38, 45, 0.7)" },  // Mare Imbrium
      { x: 490, y: 150, rx: 45, ry: 40, color: "rgba(36, 39, 46, 0.65)" }, // Mare Serenitatis
      { x: 550, y: 190, rx: 50, ry: 45, color: "rgba(34, 37, 44, 0.68)" }, // Mare Tranquillitatis
      { x: 630, y: 170, rx: 35, ry: 30, color: "rgba(32, 35, 42, 0.72)" }, // Mare Crisium
      { x: 450, y: 260, rx: 55, ry: 45, color: "rgba(40, 43, 50, 0.6)" },  // Mare Nubium
    ];

    // Major impact craters with bright ejecta ray structures (Tycho, Copernicus, Kepler)
    interface Crater {
      x: number;
      y: number;
      r: number;
      isMajor: boolean;
      rays?: number;
    }
    const craters: Crater[] = [];

    // Tycho crater (Southern highlands, huge ray system)
    craters.push({ x: 420, y: 310, r: 16, isMajor: true, rays: 12 });
    // Copernicus (prominent crater in Oceanus Procellarum)
    craters.push({ x: 350, y: 195, r: 18, isMajor: true, rays: 9 });
    // Kepler
    craters.push({ x: 300, y: 205, r: 11, isMajor: true, rays: 6 });
    // Aristarchus (brightest feature)
    craters.push({ x: 280, y: 145, r: 10, isMajor: true, rays: 5 });

    // Hundreds of medium & small realistic craters
    for (let i = 0; i < 220; i++) {
      craters.push({
        x: rnd() * mapWidth,
        y: rnd() * mapHeight,
        r: rnd() * 6 + 1.5,
        isMajor: false,
      });
    }

    // ── 3. GEOSPATIAL FEATURE KEYPOINTS (For Phase 3 matching) ──
    const keypoints: Keypoint[] = [
      { u: -0.28, v: -0.15, label: "TMC-KP-018", score: "0.994", pairU: -0.25, pairV: -0.13 },
      { u: 0.12,  v: -0.22, label: "OHRC-KP-042", score: "0.988", pairU: 0.14,  pairV: -0.20 },
      { u: -0.05, v: 0.18,  label: "OHRC-KP-089", score: "0.991", pairU: -0.03, pairV: 0.20 },
      { u: 0.28,  v: 0.12,  label: "TMC-KP-104", score: "0.985", pairU: 0.31,  pairV: 0.15 },
      { u: -0.35, v: 0.24,  label: "IIRS-KP-003", score: "0.979", pairU: -0.32, pairV: 0.27 },
      { u: 0.04,  v: -0.02, label: "OHRC-KP-116", score: "0.996", pairU: 0.05,  pairV: -0.01 },
      { u: -0.18, v: 0.05,  label: "TMC-KP-077", score: "0.992", pairU: -0.15, pairV: 0.07 },
      { u: 0.22,  v: -0.10, label: "OHRC-KP-152", score: "0.987", pairU: 0.25,  pairV: -0.08 },
    ];

    // ── 4. ANIMATION STATE ──
    const startTime = performance.now();
    let particles: DataParticle[] = [];
    let hasTriggeredBurst = false;

    // Timeline Configuration (Total ~8.2 seconds)
    // 0.00s - 0.60s: Deep space void & subtle stars
    // 0.60s - 2.40s: Realistic 3D Moon slowly emerges & rotates
    // 2.40s - 4.40s: Cinematic zoom toward Moon (camera flying towards surface)
    // 4.40s - 6.00s: Lunar surface reached; Geospatial grid & feature matching vectors appear
    // 6.00s - 6.80s: Digital disintegration effect (terrain breaks into data fragments, slight expansion)
    // 6.80s - 7.60s: Digital burst outward (data transformation, not fireworks)
    // 7.60s - 8.20s: Continuous reveal of website underneath, particles seamlessly blend
    // 8.20s: Complete!

    const render = (now: number) => {
      const elapsed = (now - startTime) / 1000;
      const cx = width / 2;
      const cy = height / 2;

      // Clear with deep space near-black
      ctx.fillStyle = "#020408";
      ctx.fillRect(0, 0, width, height);

      // ── DRAW SUBTLE DEEP-SPACE STARS ──
      for (const s of stars) {
        const flicker = 0.7 + 0.3 * Math.sin(now * s.pulseSpeed + s.pulseOffset);
        ctx.fillStyle = `rgba(220, 230, 245, ${s.baseAlpha * flicker})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      }

      // ── TIMELINE PARAMETERS ──
      let moonAlpha = 0;
      let moonRadius = 140;
      let rotSpeed = 0.22; // smooth continuous rotation
      let rot = elapsed * rotSpeed;
      let zoomProgress = 0; // 0 to 1
      let surfaceDataAlpha = 0; // geospatial matching layer
      let disintegrationProgress = 0; // digital breaking
      let canvasRevealAlpha = 1.0; // fading out canvas overlay at the very end

      if (elapsed < 0.6) {
        // Space void
        moonAlpha = 0;
      } else if (elapsed >= 0.6 && elapsed < 2.4) {
        // Emergence & smooth rotation
        const p = (elapsed - 0.6) / 1.8;
        moonAlpha = Math.min(1, p * p);
        moonRadius = 140;
      } else if (elapsed >= 2.4 && elapsed < 4.4) {
        // Cinematic Camera Zoom toward surface
        moonAlpha = 1.0;
        zoomProgress = (elapsed - 2.4) / 2.0; // 0 to 1
        // Smooth quintic acceleration flight
        const easeZoom = zoomProgress * zoomProgress * (3 - 2 * zoomProgress);
        const maxRadius = Math.max(width, height) * 0.95;
        moonRadius = 140 + easeZoom * (maxRadius - 140);
        rotSpeed = 0.22 + easeZoom * 0.45;
        rot = elapsed * rotSpeed;
      } else if (elapsed >= 4.4 && elapsed < 6.0) {
        // Camera on lunar surface: geospatial data matching
        moonAlpha = 1.0;
        moonRadius = Math.max(width, height) * 0.95;
        zoomProgress = 1.0;
        // Surface geospatial vectors fade in
        const p = (elapsed - 4.4) / 1.6;
        surfaceDataAlpha = Math.min(1, p * 1.5);
      } else if (elapsed >= 6.0 && elapsed < 6.8) {
        // Digital disintegration & slight expansion
        moonAlpha = 1.0;
        const p = (elapsed - 6.0) / 0.8;
        disintegrationProgress = p;
        surfaceDataAlpha = 1.0 - p * 0.5;
        // Slight expansion
        const expansion = Math.sin(p * Math.PI * 0.5) * 40;
        moonRadius = Math.max(width, height) * 0.95 + expansion;
      } else if (elapsed >= 6.8) {
        // Post-burst: Moon itself has deconstructed into data particles
        moonAlpha = 0;
        moonRadius = 0;
      }

      // ── TRIGGER DIGITAL DATA BURST ──
      if (elapsed >= 6.8 && !hasTriggeredBurst) {
        hasTriggeredBurst = true;

        // Generate 1,800+ digital data particles (not fire, not fireworks: pure data/voxels/coordinates)
        const dataColors = [
          "#38bdf8", // cyan
          "#ffffff", // pure white data
          "#818cf8", // soft indigo
          "#94a3b8", // lunar silver
          "#34d399", // telemetry emerald
          "#e2e8f0", // platinum
        ];

        const bits = ["01", "10", "11", "00", "λ", "Δx", "Δy", "70.9°S", "22.8°E", "RANSAC", "OHRC", "TMC-2"];

        particles = [];
        const numParticles = 1800;
        for (let i = 0; i < numParticles; i++) {
          const angle = Math.random() * Math.PI * 2;
          const speed = Math.random() * 24 + 3;
          const pType: "dot" | "cross" | "coord" | "bit" = 
            i < 1400 ? "dot" : i < 1650 ? "cross" : i < 1750 ? "bit" : "coord";

          particles.push({
            x: cx + (Math.random() - 0.5) * (width * 0.7),
            y: cy + (Math.random() - 0.5) * (height * 0.7),
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            size: pType === "dot" ? Math.random() * 2.5 + 0.8 : Math.random() * 5 + 3,
            color: dataColors[Math.floor(Math.random() * dataColors.length)],
            alpha: 0.95,
            decay: Math.random() * 0.018 + 0.012,
            type: pType,
            text: bits[Math.floor(Math.random() * bits.length)],
            angle: Math.random() * Math.PI * 2,
            vRot: (Math.random() - 0.5) * 0.1,
          });
        }
      }

      // ── RENDER 3D PHOTOREALISTIC MOON (Until burst) ──
      if (moonAlpha > 0 && moonRadius > 0) {
        ctx.save();
        ctx.globalAlpha = moonAlpha;

        // 1. Subtle, realistic Lunar Exosphere Rim Lighting (Non-cartoonish)
        const rimGrad = ctx.createRadialGradient(
          cx, cy, moonRadius * 0.96,
          cx, cy, moonRadius * 1.05
        );
        rimGrad.addColorStop(0, "rgba(200, 225, 255, 0.22)");
        rimGrad.addColorStop(0.4, "rgba(56, 189, 248, 0.12)");
        rimGrad.addColorStop(1, "rgba(2, 4, 8, 0)");
        ctx.fillStyle = rimGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, moonRadius * 1.05, 0, Math.PI * 2);
        ctx.fill();

        // 2. Base Moon Sphere with True 3D Spherical Clipping
        ctx.beginPath();
        ctx.arc(cx, cy, moonRadius, 0, Math.PI * 2);
        ctx.clip();

        // Physically Realistic Directional Sun Lighting Gradient
        // Sun vector from upper-right: (0.7, -0.3, 0.65)
        const lightOffsetX = moonRadius * 0.4;
        const lightOffsetY = -moonRadius * 0.35;
        const sphereGrad = ctx.createRadialGradient(
          cx + lightOffsetX, cy + lightOffsetY, moonRadius * 0.08,
          cx, cy, moonRadius * 1.15
        );
        // Realistic lunar regolith albedos (highlands vs dark basalt)
        sphereGrad.addColorStop(0, "#d1d5db");    // Bright highland sunlit peak
        sphereGrad.addColorStop(0.35, "#9ca3af"); // Mid-tone lunar gray
        sphereGrad.addColorStop(0.65, "#4b5563"); // Low-angle illumination
        sphereGrad.addColorStop(0.85, "#1f242d"); // Terminator twilight
        sphereGrad.addColorStop(1.0, "#080a0f");  // Unlit dark side
        ctx.fillStyle = sphereGrad;
        ctx.fillRect(cx - moonRadius, cy - moonRadius, moonRadius * 2, moonRadius * 2);

        // 3. Basaltic Maria (Projected on 3D Sphere with continuous rotation)
        for (const m of maria) {
          const mLong = (m.x + rot * 75) % mapWidth;
          const u = (mLong / mapWidth) * 2 - 1; // -1 to 1
          const v = (m.y / mapHeight) * 2 - 1;

          if (u * u + v * v < 0.95) {
            const z = Math.sqrt(Math.max(0, 1 - u * u - v * v));
            const px = cx + u * moonRadius;
            const py = cy + v * moonRadius;
            const prx = m.rx * (moonRadius / 150) * z;
            const pry = m.ry * (moonRadius / 150) * z;

            // Directional sun illumination factor
            const sunFactor = Math.max(0, 0.6 * u - 0.4 * v + 0.7 * z);
            if (sunFactor > 0.05) {
              ctx.save();
              ctx.translate(px, py);
              ctx.scale(1, pry / Math.max(1, prx));
              const mareGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, prx);
              mareGrad.addColorStop(0, m.color);
              mareGrad.addColorStop(0.7, "rgba(30, 33, 40, 0.4)");
              mareGrad.addColorStop(1, "rgba(30, 33, 40, 0)");
              ctx.fillStyle = mareGrad;
              ctx.beginPath();
              ctx.arc(0, 0, prx, 0, Math.PI * 2);
              ctx.fill();
              ctx.restore();
            }
          }
        }

        // 4. Crater Rays (Tycho & Copernicus bright ejecta lines)
        for (const c of craters) {
          if (c.isMajor && c.rays) {
            const cLong = (c.x + rot * 75) % mapWidth;
            const u = (cLong / mapWidth) * 2 - 1;
            const v = (c.y / mapHeight) * 2 - 1;
            if (u * u + v * v < 0.92) {
              const z = Math.sqrt(Math.max(0, 1 - u * u - v * v));
              const px = cx + u * moonRadius;
              const py = cy + v * moonRadius;
              const sunFactor = Math.max(0, 0.6 * u - 0.4 * v + 0.7 * z);

              if (sunFactor > 0.1) {
                ctx.save();
                ctx.strokeStyle = `rgba(240, 245, 255, ${0.25 * sunFactor})`;
                ctx.lineWidth = 0.8 * (moonRadius / 140);
                for (let rIdx = 0; rIdx < c.rays; rIdx++) {
                  const rAngle = (rIdx / c.rays) * Math.PI * 2 + c.x * 0.01;
                  const rayLen = (moonRadius * 0.45 + (rIdx % 3) * 25) * z;
                  ctx.beginPath();
                  ctx.moveTo(px, py);
                  ctx.lineTo(px + Math.cos(rAngle) * rayLen, py + Math.sin(rAngle) * rayLen);
                  ctx.stroke();
                }
                ctx.restore();
              }
            }
          }
        }

        // 5. Craters & Rim Shadow Modeling
        for (const crater of craters) {
          const cLong = (crater.x + rot * 75) % mapWidth;
          const u = (cLong / mapWidth) * 2 - 1;
          const v = (crater.y / mapHeight) * 2 - 1;

          if (u * u + v * v < 0.96) {
            const z = Math.sqrt(Math.max(0, 1 - u * u - v * v));
            const px = cx + u * moonRadius;
            const py = cy + v * moonRadius;
            const pr = crater.r * (moonRadius / 140) * (0.5 + 0.5 * z);

            const sunFactor = 0.6 * u - 0.4 * v + 0.7 * z;
            if (sunFactor > 0.05) {
              // Crater interior shadow (facing away from sun)
              ctx.fillStyle = `rgba(18, 20, 26, ${0.65 * sunFactor})`;
              ctx.beginPath();
              ctx.arc(px + pr * 0.2, py - pr * 0.15, Math.max(0.5, pr * 0.9), 0, Math.PI * 2);
              ctx.fill();

              // Crater sunlit elevated rim
              ctx.strokeStyle = `rgba(240, 245, 255, ${0.5 * sunFactor})`;
              ctx.lineWidth = Math.max(0.5, 0.8 * (moonRadius / 140));
              ctx.beginPath();
              ctx.arc(px, py, Math.max(0.8, pr), 0, Math.PI * 2);
              ctx.stroke();
            }
          }
        }

        // 6. Deep Natural Terminator Shadow (Day/Night dividing curve)
        const terminatorGrad = ctx.createRadialGradient(
          cx + lightOffsetX, cy + lightOffsetY, moonRadius * 0.5,
          cx - lightOffsetX * 0.7, cy - lightOffsetY * 0.7, moonRadius * 1.05
        );
        terminatorGrad.addColorStop(0, "rgba(0, 0, 0, 0)");
        terminatorGrad.addColorStop(0.5, "rgba(5, 7, 12, 0.2)");
        terminatorGrad.addColorStop(0.8, "rgba(2, 3, 6, 0.85)");
        terminatorGrad.addColorStop(1, "rgba(1, 2, 4, 0.98)");
        ctx.fillStyle = terminatorGrad;
        ctx.fillRect(cx - moonRadius, cy - moonRadius, moonRadius * 2, moonRadius * 2);

        // ── 7. PHASE 3: GEOSPATIAL DATA LAYER OVER LUNAR SURFACE (4.4s - 6.0s) ──
        if (surfaceDataAlpha > 0) {
          ctx.save();
          ctx.globalAlpha = surfaceDataAlpha;

          // A. Geodetic Coordinate Grid (Latitude & Longitude lines)
          ctx.strokeStyle = "rgba(56, 189, 248, 0.28)"; // subtle cyan
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 6]);

          // Latitude lines
          for (let lat = -60; lat <= 60; lat += 20) {
            const rad = (lat * Math.PI) / 180;
            const yOffset = Math.sin(rad) * moonRadius * 0.85;
            const rWidth = Math.cos(rad) * moonRadius;
            ctx.beginPath();
            ctx.ellipse(cx, cy + yOffset, rWidth, rWidth * 0.28, 0, 0, Math.PI * 2);
            ctx.stroke();
          }

          // Longitude lines
          for (let lon = 0; lon < 6; lon++) {
            const lonAngle = rot * 0.5 + (lon * Math.PI) / 6;
            const xOffset = Math.cos(lonAngle) * moonRadius * 0.9;
            ctx.beginPath();
            ctx.ellipse(cx, cy, Math.abs(xOffset), moonRadius, 0, 0, Math.PI * 2);
            ctx.stroke();
          }
          ctx.setLineDash([]);

          // B. High-Precision Feature Correspondence Matches (Tie-lines between keypoints)
          for (let i = 0; i < keypoints.length; i++) {
            const kp = keypoints[i];
            const kx = cx + kp.u * moonRadius * 0.8;
            const ky = cy + kp.v * moonRadius * 0.8;
            const px = cx + kp.pairU * moonRadius * 0.8;
            const py = cy + kp.pairV * moonRadius * 0.8;

            // Target crosshairs
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.2;
            const ch = 8;
            // Crosshair +
            ctx.beginPath();
            ctx.moveTo(kx - ch, ky); ctx.lineTo(kx + ch, ky);
            ctx.moveTo(kx, ky - ch); ctx.lineTo(kx, ky + ch);
            ctx.stroke();

            // Inner target circle
            ctx.beginPath();
            ctx.arc(kx, ky, 3, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(56, 189, 248, 0.8)";
            ctx.fill();

            // Vector correspondence tie-line to matched sensor point
            ctx.strokeStyle = "rgba(52, 211, 153, 0.75)"; // emerald match line
            ctx.lineWidth = 1.0;
            ctx.setLineDash([2, 3]);
            ctx.beginPath();
            ctx.moveTo(kx, ky);
            ctx.lineTo(px, py);
            ctx.stroke();
            ctx.setLineDash([]);

            // Matched target cross
            ctx.strokeStyle = "#34d399";
            ctx.beginPath();
            ctx.arc(px, py, 4, 0, Math.PI * 2);
            ctx.stroke();

            // Coordinate labels (Minimal, scientific)
            ctx.font = "9px 'JetBrains Mono', monospace";
            ctx.fillStyle = "rgba(240, 245, 255, 0.85)";
            ctx.fillText(`${kp.label} [${kp.score}]`, kx + 10, ky - 6);
          }

          // C. Geodetic HUD Telemetry in Corners of Surface
          ctx.font = "10px 'JetBrains Mono', monospace";
          ctx.fillStyle = "rgba(56, 189, 248, 0.75)";
          ctx.fillText("SELORA // GEODETIC CORRESPONDENCE ENGINE", cx - 180, cy - moonRadius * 0.75);
          ctx.fillStyle = "rgba(148, 163, 184, 0.65)";
          ctx.fillText("TARGET: LUNAR SOUTH POLE • SUB-PIXEL RMSE: 0.18px", cx - 180, cy - moonRadius * 0.75 + 16);

          ctx.restore();
        }

        // ── 8. PHASE 4: DIGITAL DISINTEGRATION LATTICE (6.0s - 6.8s) ──
        if (disintegrationProgress > 0) {
          ctx.save();
          // Voxel grid breaking effect
          const gridCount = 28;
          const gridSize = (moonRadius * 2) / gridCount;
          ctx.strokeStyle = `rgba(56, 189, 248, ${disintegrationProgress * 0.8})`;
          ctx.lineWidth = 1;

          for (let gx = 0; gx < gridCount; gx++) {
            for (let gy = 0; gy < gridCount; gy++) {
              const xPos = cx - moonRadius + gx * gridSize;
              const yPos = cy - moonRadius + gy * gridSize;
              const distFromCenter = Math.hypot(xPos - cx, yPos - cy);

              if (distFromCenter < moonRadius) {
                // Fragment dispersion offset
                const jitterX = (Math.sin(gx * 7 + elapsed * 10) * 12) * disintegrationProgress;
                const jitterY = (Math.cos(gy * 7 + elapsed * 10) * 12) * disintegrationProgress;
                ctx.strokeRect(xPos + jitterX, yPos + jitterY, gridSize * 0.9, gridSize * 0.9);
              }
            }
          }

          // Digital glow shimmer
          const digiGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, moonRadius);
          digiGrad.addColorStop(0, `rgba(56, 189, 248, ${disintegrationProgress * 0.4})`);
          digiGrad.addColorStop(0.7, `rgba(129, 140, 248, ${disintegrationProgress * 0.25})`);
          digiGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
          ctx.fillStyle = digiGrad;
          ctx.fillRect(cx - moonRadius, cy - moonRadius, moonRadius * 2, moonRadius * 2);

          ctx.restore();
        }

        ctx.restore();
      }

      // ── 9. DRAW DIGITAL DATA PARTICLES (Burst Transformation) ──
      if (hasTriggeredBurst) {
        ctx.save();
        for (const p of particles) {
          if (p.alpha > 0) {
            p.x += p.vx;
            p.y += p.vy;
            p.vx *= 0.975; // gentle aerodynamic drag
            p.vy *= 0.975;
            p.alpha -= p.decay;

            ctx.globalAlpha = Math.max(0, p.alpha);

            if (p.type === "dot") {
              ctx.fillStyle = p.color;
              ctx.shadowColor = p.color;
              ctx.shadowBlur = 6;
              ctx.beginPath();
              ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
              ctx.fill();
            } else if (p.type === "cross") {
              ctx.strokeStyle = p.color;
              ctx.lineWidth = 1;
              p.angle += p.vRot;
              ctx.save();
              ctx.translate(p.x, p.y);
              ctx.rotate(p.angle);
              const sz = p.size;
              ctx.beginPath();
              ctx.moveTo(-sz, 0); ctx.lineTo(sz, 0);
              ctx.moveTo(0, -sz); ctx.lineTo(0, sz);
              ctx.stroke();
              ctx.restore();
            } else if (p.type === "coord" || p.type === "bit") {
              ctx.font = "8px 'JetBrains Mono', monospace";
              ctx.fillStyle = p.color;
              ctx.fillText(p.text || "10", p.x, p.y);
            }
          }
        }
        ctx.restore();

        // Reveal the website by smoothly dissolving the background overlay
        if (elapsed >= 7.6) {
          const dissolveProgress = (elapsed - 7.6) / 0.6; // 0 to 1
          canvasRevealAlpha = Math.max(0, 1 - dissolveProgress);
          if (canvas) {
            canvas.style.opacity = `${canvasRevealAlpha}`;
          }
        }
      }

      // Complete and handoff to SELORA Landing Page (~8.2s)
      if (elapsed >= 8.2) {
        cancelAnimationFrame(animFrameRef.current);
        handleFinish();
        return;
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("resize", handleResize);
    };
  }, [handleFinish, onComplete]);

  return (
    <AnimatePresence>
      {!isDismissing && (
        <motion.div
          key="cinematic-intro-overlay"
          initial={{ opacity: 1 }}
          exit={{
            opacity: 0,
            transition: { duration: 0.5, ease: "easeOut" },
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            backgroundColor: "#020408",
            overflow: "hidden",
            cursor: "default",
          }}
        >
          {/* Main 60fps Canvas for Space, Photorealistic Moon, Surface flight & Digital Disintegration */}
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              display: "block",
              transition: "opacity 0.4s ease-out",
            }}
          />

          {/* Minimal, Subtle Aerospace HUD Header during intro */}
          <div
            style={{
              position: "absolute",
              top: 24,
              left: 28,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              gap: 12,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              letterSpacing: "0.08em",
              color: "rgba(148, 163, 184, 0.6)",
              pointerEvents: "none",
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#38bdf8",
                boxShadow: "0 0 8px #38bdf8",
              }}
            />
            <span>SELORA // LUNAR MISSION SEQUENCE</span>
          </div>

          {/* Minimal, Premium "Skip Intro" Button */}
          <button
            onClick={handleFinish}
            style={{
              position: "absolute",
              top: 24,
              right: 28,
              zIndex: 20,
              background: "rgba(15, 23, 42, 0.5)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              backdropFilter: "blur(8px)",
              color: "rgba(226, 232, 240, 0.8)",
              padding: "6px 14px",
              borderRadius: "20px",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              letterSpacing: "0.06em",
              cursor: "pointer",
              transition: "all 0.2s ease",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.5)";
              e.currentTarget.style.color = "#ffffff";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.12)";
              e.currentTarget.style.color = "rgba(226, 232, 240, 0.8)";
            }}
          >
            <span>Skip Intro</span>
            <span style={{ fontSize: 9, opacity: 0.6 }}>⏩</span>
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
