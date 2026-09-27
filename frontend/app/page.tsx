"use client";

import { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import {
  Satellite, ChevronRight, Zap, Shield, BarChart3,
  Layers, ArrowRight, Orbit, Sparkles,
} from "lucide-react";
import LaunchAnimation from "@/components/ui/LaunchAnimation";

// Dynamically import to avoid SSR issues with Three.js
const MoonScene = dynamic(() => import("@/components/three/MoonScene"), {
  ssr: false,
  loading: () => null,
});

const FEATURES = [
  {
    icon: Layers,
    title: "Sensor-Aware Pipeline",
    desc: "Adapts preprocessing, feature extraction, and matching to OHRC, TMC-2, and IIRS sensor characteristics.",
    gradient: "linear-gradient(135deg, #00c8ff22, #6366f122)",
  },
  {
    icon: Zap,
    title: "Multi-Scale Registration",
    desc: "Image pyramids enable robust matching despite significant resolution differences between sensors.",
    gradient: "linear-gradient(135deg, #6366f122, #a855f722)",
  },
  {
    icon: Shield,
    title: "Geometric Verification",
    desc: "RANSAC with USAC_MAGSAC rejects outliers. Multi-model comparison selects the most stable transform.",
    gradient: "linear-gradient(135deg, #00c8ff22, #22d3a522)",
  },
  {
    icon: BarChart3,
    title: "Quantitative Confidence",
    desc: "Every registration produces RMSE, inlier ratio, spatial coverage, and a documented confidence score.",
    gradient: "linear-gradient(135deg, #22d3a522, #00c8ff22)",
  },
];

const SENSORS = [
  { name: "OHRC", res: "~25cm", desc: "High Resolution Camera", icon: "🔬" },
  { name: "TMC-2", res: "~5m", desc: "Terrain Mapping Camera", icon: "🛰️" },
  { name: "IIRS", res: "~80m", desc: "IR Spectrometer", icon: "📡" },
];

const PIPELINE_STAGES = [
  "Sensor Analysis",
  "Intensity Normalization",
  "Multi-Scale Pyramid",
  "Feature Extraction",
  "Descriptor Matching",
  "RANSAC Verification",
  "Transformation Estimation",
  "Image Warping",
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  }),
};

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

export default function LandingPage() {
  const [showLaunch, setShowLaunch] = useState(true);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)", position: "relative" }}>
      {/* ── Cinematic Launch Sequence Animation ── */}
      {showLaunch && (
        <LaunchAnimation onComplete={() => setShowLaunch(false)} />
      )}

      {/* ── 3D Background ── */}
      <MoonScene />

      {/* ── Content Layer ── */}
      <div style={{ position: "relative", zIndex: 1 }}>

        {/* ── Nav ── */}
        <nav className="glass-nav">
          <div
            style={{
              maxWidth: 1200,
              margin: "0 auto",
              padding: "0 2rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              height: 64,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div className="nav-logo-glow">
                <Satellite size={18} color="var(--accent-cyan)" />
              </div>
              <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "0.08em" }}>
                SELORA
              </span>
              <span className="badge badge-cyan" style={{ marginLeft: 4 }}>
                SIH 2026
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                onClick={() => setShowLaunch(true)}
                className="btn-glass"
                style={{ fontSize: 12, padding: "6px 14px", display: "flex", alignItems: "center", gap: 6 }}
                title="Replay Cinematic Intro"
              >
                <Sparkles size={13} color="var(--accent-cyan)" />
                <span>Replay Intro</span>
              </button>
              <Link href="/benchmark">
                <button className="btn-glass">Benchmark</button>
              </Link>
              <Link href="/workspace">
                <button className="btn-primary">
                  Launch Workspace <ArrowRight size={14} />
                </button>
              </Link>
            </div>
          </div>
        </nav>

        {/* ── Hero ── */}
        <section style={{ padding: "140px 2rem 100px", textAlign: "center", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <motion.div
            style={{ maxWidth: 780, margin: "0 auto" }}
            initial="hidden"
            animate="visible"
            variants={staggerContainer}
          >
            {/* Orbit badge */}
            <motion.div variants={fadeUp} custom={0} style={{ marginBottom: 28 }}>
              <div className="hero-orbit-badge">
                <Orbit size={14} />
                <span>ISRO CHANDRAYAAN-2 SCIENCE NETWORK • PS 26166</span>
              </div>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              custom={1}
              style={{
                fontSize: "clamp(3.2rem, 8vw, 5.2rem)",
                fontWeight: 900,
                lineHeight: 1.02,
                marginBottom: 16,
                letterSpacing: "-0.03em",
              }}
            >
              <span style={{ color: "var(--text-primary)" }}>SELORA</span>
            </motion.h1>

            <motion.div
              variants={fadeUp}
              custom={2}
              style={{
                fontSize: "clamp(1.2rem, 3.2vw, 1.85rem)",
                fontWeight: 700,
                lineHeight: 1.3,
                marginBottom: 24,
                letterSpacing: "-0.015em",
              }}
            >
              <span className="hero-gradient-text">
                Cross-Mission Lunar Image Correspondence & Registration
              </span>
            </motion.div>

            <motion.p
              variants={fadeUp}
              custom={3}
              style={{
                fontSize: "1.1rem",
                color: "var(--text-secondary)",
                marginBottom: 16,
                lineHeight: 1.7,
              }}
            >
              Aligning the Moon across sensors, scales, and illumination conditions.
            </motion.p>

            <motion.p
              variants={fadeUp}
              custom={4}
              style={{
                fontSize: "0.9rem",
                color: "var(--text-muted)",
                marginBottom: 48,
                maxWidth: 540,
                margin: "0 auto 48px",
                lineHeight: 1.7,
              }}
            >
              SELORA dynamically adapts its registration pipeline to the characteristics
              of Chandrayaan-2 OHRC, TMC-2, and IIRS sensor pairs — producing geometrically
              verified, aligned lunar imagery with quantitative confidence metrics.
            </motion.p>

            <motion.div
              variants={fadeUp}
              custom={5}
              style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}
            >
              <Link href="/workspace">
                <button className="btn-hero-primary">
                  <Sparkles size={16} />
                  Launch Workspace
                </button>
              </Link>
              <Link href="/benchmark">
                <button className="btn-hero-secondary">
                  <BarChart3 size={16} />
                  View Benchmark
                </button>
              </Link>
            </motion.div>

            {/* Scroll indicator */}
            <motion.div
              variants={fadeUp}
              custom={5}
              className="scroll-indicator"
              style={{ marginTop: 80 }}
            >
              <div className="scroll-line" />
            </motion.div>
          </motion.div>
        </section>

        {/* ── Sensor Cards ── */}
        <section style={{ maxWidth: 1000, margin: "0 auto", padding: "0 2rem 80px" }}>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
            style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}
          >
            {SENSORS.map((s, i) => (
              <motion.div key={s.name} variants={fadeUp} custom={i}>
                <div className="glass-card sensor-card-3d">
                  <div className="sensor-icon-ring">
                    <span style={{ fontSize: 28 }}>{s.icon}</span>
                  </div>
                  <div
                    className="text-glow-cyan"
                    style={{ fontSize: "1.6rem", fontWeight: 800, marginBottom: 4 }}
                  >
                    {s.name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: 10 }}>
                    {s.desc}
                  </div>
                  <div className="badge badge-cyan">{s.res} GSD</div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* ── Pipeline Visualization ── */}
        <section style={{ maxWidth: 1000, margin: "0 auto", padding: "0 2rem 80px" }}>
          <motion.div
            className="glass-card"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeUp}
            custom={0}
          >
            <div className="text-label" style={{ textAlign: "center", marginBottom: 28 }}>
              End-to-End Registration Pipeline
            </div>
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}
            >
              {PIPELINE_STAGES.map((stage, i) => (
                <motion.div key={stage} variants={fadeUp} custom={i}>
                  <div className="pipeline-step-3d">
                    <span className="pipeline-num">{String(i + 1).padStart(2, "0")}</span>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{stage}</span>
                    {i < PIPELINE_STAGES.length - 1 && <div className="pipeline-connector" />}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        </section>

        {/* ── Features ── */}
        <section style={{ maxWidth: 1000, margin: "0 auto", padding: "0 2rem 80px" }}>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
            style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}
          >
            {FEATURES.map(({ icon: Icon, title, desc, gradient }, i) => (
              <motion.div key={title} variants={fadeUp} custom={i}>
                <div className="glass-card feature-card-3d" style={{ background: gradient }}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                    <div className="feature-icon-box">
                      <Icon size={20} color="var(--accent-cyan)" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: "var(--text-primary)" }}>
                        {title}
                      </div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                        {desc}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* ── CTA Banner ── */}
        <section style={{ padding: "0 2rem 100px" }}>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            custom={0}
          >
            <div className="glass-card cta-banner-3d" style={{ maxWidth: 800, margin: "0 auto", textAlign: "center", padding: "60px 40px" }}>
              <div className="cta-glow-line" />
              <h2 style={{ fontSize: "1.9rem", fontWeight: 800, marginBottom: 14, letterSpacing: "-0.02em" }}>
                Ready to register lunar imagery?
              </h2>
              <p style={{ color: "var(--text-secondary)", marginBottom: 36, fontSize: 15 }}>
                Upload your source and reference images. SELORA handles the rest.
              </p>
              <Link href="/workspace">
                <button className="btn-hero-primary" style={{ fontSize: 15 }}>
                  Open Workspace <ChevronRight size={16} />
                </button>
              </Link>
            </div>
          </motion.div>
        </section>

        {/* ── Footer ── */}
        <footer className="glass-footer" style={{ textAlign: "center" }}>
          <div>
            SELORA · SIH Problem Statement 26166 · Space Technology / Computer Vision / Lunar Science
          </div>
          <div style={{ marginTop: 4, color: "var(--text-muted)" }}>
            Chandrayaan-2 OHRC · TMC-2 · IIRS Registration Framework
          </div>
        </footer>
      </div>
    </div>
  );
}
