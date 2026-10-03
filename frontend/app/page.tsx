"use client";

import { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion, useScroll, useTransform } from "framer-motion";
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
    gradient: "linear-gradient(135deg, rgba(0,200,255,0.08), rgba(99,102,241,0.08))",
    border: "rgba(0, 200, 255, 0.3)",
  },
  {
    icon: Zap,
    title: "Multi-Scale Registration",
    desc: "Image pyramids enable robust matching despite significant resolution differences between sensors.",
    gradient: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.08))",
    border: "rgba(168, 85, 247, 0.3)",
  },
  {
    icon: Shield,
    title: "Geometric Verification",
    desc: "RANSAC with USAC_MAGSAC rejects outliers. Multi-model comparison selects the most stable transform.",
    gradient: "linear-gradient(135deg, rgba(0,200,255,0.08), rgba(34,211,165,0.08))",
    border: "rgba(34, 211, 165, 0.3)",
  },
  {
    icon: BarChart3,
    title: "Quantitative Confidence",
    desc: "Every registration produces RMSE, inlier ratio, spatial coverage, and a documented confidence score.",
    gradient: "linear-gradient(135deg, rgba(34,211,165,0.08), rgba(0,200,255,0.08))",
    border: "rgba(0, 200, 255, 0.3)",
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
  hidden: { opacity: 0, y: 40, filter: "blur(10px)", scale: 0.95 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    scale: 1,
    transition: { 
      delay: i * 0.1, 
      duration: 0.8, 
      ease: [0.16, 1, 0.3, 1] as const
    },
  }),
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 } 
  },
};

export default function LandingPage() {
  const [showLaunch, setShowLaunch] = useState(true);
  
  // Parallax effects
  const { scrollY } = useScroll();
  
  const yHero = useTransform(scrollY, [0, 800], [0, 250]);
  const opacityHero = useTransform(scrollY, [0, 400], [1, 0]);
  const scaleHero = useTransform(scrollY, [0, 400], [1, 0.9]);

  const yBgGlow1 = useTransform(scrollY, [0, 1000], [0, 300]);
  const yBgGlow2 = useTransform(scrollY, [0, 1000], [0, -300]);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)", position: "relative", overflowX: "hidden" }}>
      {/* ── Cinematic Launch Sequence Animation ── */}
      {showLaunch && (
        <LaunchAnimation onComplete={() => setShowLaunch(false)} />
      )}

      {/* ── 3D Background ── */}
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 0, pointerEvents: "none" }}>
        <MoonScene />
      </div>

      {/* ── Ambient Background Glows ── */}
      <motion.div 
        style={{
          position: "fixed",
          top: "10%",
          left: "-10%",
          width: "50vw",
          height: "50vw",
          background: "radial-gradient(circle, rgba(0,200,255,0.06) 0%, transparent 60%)",
          filter: "blur(80px)",
          zIndex: 0,
          y: yBgGlow1
        }}
      />
      <motion.div 
        style={{
          position: "fixed",
          bottom: "10%",
          right: "-10%",
          width: "40vw",
          height: "40vw",
          background: "radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 60%)",
          filter: "blur(80px)",
          zIndex: 0,
          y: yBgGlow2
        }}
      />

      {/* ── Content Layer ── */}
      <div style={{ position: "relative", zIndex: 1 }}>

        {/* ── Nav ── */}
        <motion.nav 
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="glass-nav"
        >
          <div
            style={{
              maxWidth: 1200,
              margin: "0 auto",
              padding: "0 2rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              height: 70,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <motion.div 
                whileHover={{ rotate: 90, scale: 1.1 }}
                transition={{ duration: 0.4 }}
                className="nav-logo-glow"
              >
                <Satellite size={20} color="var(--accent-cyan)" />
              </motion.div>
              <span style={{ fontWeight: 800, fontSize: 18, letterSpacing: "0.1em", textShadow: "0 0 10px rgba(0,200,255,0.4)" }}>
                SELORA
              </span>
            </div>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowLaunch(true)}
                className="btn-glass"
                style={{ fontSize: 13, padding: "8px 16px", display: "flex", alignItems: "center", gap: 6 }}
                title="Replay Cinematic Intro"
              >
                <Sparkles size={14} color="var(--accent-cyan)" />
                <span className="hidden sm:inline">Replay Intro</span>
              </motion.button>
              <Link href="/benchmark">
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="btn-glass">Benchmark</motion.button>
              </Link>
              <Link href="/workspace">
                <motion.button 
                  whileHover={{ scale: 1.05, boxShadow: "0 0 20px rgba(0,200,255,0.5)" }} 
                  whileTap={{ scale: 0.95 }} 
                  className="btn-primary"
                >
                  Workspace <ArrowRight size={16} />
                </motion.button>
              </Link>
            </div>
          </div>
        </motion.nav>

        {/* ── Hero ── */}
        <section style={{ padding: "160px 2rem 120px", textAlign: "center", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <motion.div
            style={{ maxWidth: 820, margin: "0 auto", y: yHero, opacity: opacityHero, scale: scaleHero }}
            initial="hidden"
            animate="visible"
            variants={staggerContainer}
          >
            {/* Orbit badge */}
            <motion.div variants={fadeUp} custom={0} style={{ marginBottom: 32, display: "flex", justifyContent: "center" }}>
              <motion.div 
                whileHover={{ scale: 1.05, borderColor: "rgba(0, 200, 255, 0.5)" }}
                className="hero-orbit-badge glass-card"
                style={{ padding: "8px 20px", borderRadius: 30, background: "rgba(0,200,255,0.05)" }}
              >
                <Orbit size={16} className="pulse-glow" />
                <span style={{ letterSpacing: "0.08em" }}>ISRO CHANDRAYAAN-2 SCIENCE NETWORK</span>
              </motion.div>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              custom={1}
              style={{
                fontSize: "clamp(3.5rem, 9vw, 6rem)",
                fontWeight: 900,
                lineHeight: 1.05,
                marginBottom: 20,
                letterSpacing: "-0.04em",
                textShadow: "0 10px 30px rgba(0,0,0,0.5)"
              }}
            >
              <span style={{ color: "var(--text-primary)" }}>SELORA</span>
            </motion.h1>

            <motion.div
              variants={fadeUp}
              custom={2}
              style={{
                fontSize: "clamp(1.4rem, 3.5vw, 2.2rem)",
                fontWeight: 800,
                lineHeight: 1.4,
                marginBottom: 32,
                letterSpacing: "-0.02em",
              }}
            >
              <span className="hero-gradient-text" style={{ textShadow: "0 0 20px rgba(0,200,255,0.2)" }}>
                Cross-Mission Lunar Image Correspondence & Registration
              </span>
            </motion.div>

            <motion.p
              variants={fadeUp}
              custom={3}
              style={{
                fontSize: "1.2rem",
                color: "var(--text-secondary)",
                marginBottom: 20,
                lineHeight: 1.8,
                fontWeight: 500,
              }}
            >
              Aligning the Moon across sensors, scales, and illumination conditions.
            </motion.p>

            <motion.p
              variants={fadeUp}
              custom={4}
              style={{
                fontSize: "1rem",
                color: "var(--text-muted)",
                marginBottom: 56,
                maxWidth: 600,
                margin: "0 auto 56px",
                lineHeight: 1.8,
              }}
            >
              SELORA dynamically adapts its registration pipeline to the characteristics
              of Chandrayaan-2 OHRC, TMC-2, and IIRS sensor pairs — producing geometrically
              verified, aligned lunar imagery with quantitative confidence metrics.
            </motion.p>

            <motion.div
              variants={fadeUp}
              custom={5}
              style={{ display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }}
            >
              <Link href="/workspace">
                <motion.button 
                  whileHover={{ scale: 1.05, y: -4 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-hero-primary"
                >
                  <Sparkles size={18} />
                  Launch Workspace
                </motion.button>
              </Link>
              <Link href="/benchmark">
                <motion.button 
                  whileHover={{ scale: 1.05, y: -4, backgroundColor: "rgba(30, 37, 53, 0.8)" }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-hero-secondary"
                >
                  <BarChart3 size={18} />
                  View Benchmark
                </motion.button>
              </Link>
            </motion.div>

            {/* Scroll indicator */}
            <motion.div
              variants={fadeUp}
              custom={6}
              className="scroll-indicator"
              style={{ marginTop: 100 }}
            >
              <motion.div 
                animate={{ y: [0, 10, 0], opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                className="scroll-line" 
                style={{ height: 60, width: 2, background: "linear-gradient(180deg, var(--accent-cyan), transparent)" }}
              />
            </motion.div>
          </motion.div>
        </section>

        {/* ── Sensor Cards ── */}
        <section style={{ maxWidth: 1100, margin: "0 auto", padding: "0 2rem 120px" }}>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px", amount: 0.2 }}
            variants={staggerContainer}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 24 }}
          >
            {SENSORS.map((s, i) => (
              <motion.div key={s.name} variants={fadeUp} custom={i} whileHover={{ y: -10 }}>
                <div className="glass-card sensor-card-3d" style={{ background: "rgba(14, 17, 23, 0.4)", backdropFilter: "blur(20px)" }}>
                  <motion.div 
                    whileHover={{ rotate: 360, scale: 1.1 }}
                    transition={{ duration: 0.8 }}
                    className="sensor-icon-ring"
                  >
                    <span style={{ fontSize: 32 }}>{s.icon}</span>
                  </motion.div>
                  <div
                    className="text-glow-cyan"
                    style={{ fontSize: "1.8rem", fontWeight: 900, marginBottom: 8 }}
                  >
                    {s.name}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-muted)", letterSpacing: "0.08em", marginBottom: 16 }}>
                    {s.desc}
                  </div>
                  <div className="badge badge-cyan" style={{ fontSize: 11, padding: "4px 10px" }}>{s.res} GSD</div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* ── Pipeline Visualization ── */}
        <section style={{ maxWidth: 1100, margin: "0 auto", padding: "0 2rem 120px" }}>
          <motion.div
            className="glass-card"
            initial={{ opacity: 0, scale: 0.95, y: 50, filter: "blur(10px)" }}
            whileInView={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            style={{ background: "rgba(14, 17, 23, 0.5)", border: "1px solid rgba(0, 200, 255, 0.15)", overflow: "hidden" }}
          >
            <div className="text-label" style={{ textAlign: "center", marginBottom: 40, fontSize: 13, color: "var(--accent-cyan)", textShadow: "0 0 10px rgba(0,200,255,0.3)" }}>
              End-to-End Registration Pipeline
            </div>
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-50px" }}
              style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}
            >
              {PIPELINE_STAGES.map((stage, i) => (
                <motion.div key={stage} variants={fadeUp} custom={i} whileHover={{ scale: 1.05 }}>
                  <div className="pipeline-step-3d" style={{ background: "rgba(30, 37, 53, 0.4)", display: "flex", flexDirection: "column", alignItems: "center", padding: "20px 10px", textAlign: "center", gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: "50%", background: "rgba(0,200,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(0,200,255,0.3)", color: "var(--accent-cyan)", fontWeight: "bold", fontSize: 14, fontFamily: "monospace" }}>
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <span style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 600 }}>{stage}</span>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        </section>

        {/* ── Features ── */}
        <section style={{ maxWidth: 1100, margin: "0 auto", padding: "0 2rem 120px" }}>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px", amount: 0.1 }}
            variants={staggerContainer}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: 24 }}
          >
            {FEATURES.map(({ icon: Icon, title, desc, gradient, border }, i) => (
              <motion.div key={title} variants={fadeUp} custom={i}>
                <motion.div 
                  whileHover={{ scale: 1.02, y: -5, borderColor: border }}
                  className="glass-card feature-card-3d" 
                  style={{ background: gradient, borderColor: "rgba(30, 37, 53, 0.8)", padding: "2.5rem 2rem" }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 24 }}>
                    <div className="feature-icon-box" style={{ width: 60, height: 60, background: "rgba(0,0,0,0.3)", borderRadius: 16 }}>
                      <Icon size={30} color="var(--accent-cyan)" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: 19, marginBottom: 12, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
                        {title}
                      </div>
                      <div style={{ fontSize: 15, color: "var(--text-secondary)", lineHeight: 1.8 }}>
                        {desc}
                      </div>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* ── CTA Banner ── */}
        <section style={{ padding: "0 2rem 140px" }}>
          <motion.div
            initial={{ opacity: 0, y: 60, scale: 0.95, filter: "blur(10px)" }}
            whileInView={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="glass-card cta-banner-3d" style={{ maxWidth: 900, margin: "0 auto", textAlign: "center", padding: "80px 40px", background: "linear-gradient(180deg, rgba(14, 17, 23, 0.4) 0%, rgba(0, 200, 255, 0.05) 100%)", borderColor: "rgba(0, 200, 255, 0.2)" }}>
              <div className="cta-glow-line" />
              <motion.div 
                animate={{ scale: [1, 1.01, 1] }} 
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              >
                <h2 style={{ fontSize: "clamp(2rem, 5vw, 3.2rem)", fontWeight: 900, marginBottom: 20, letterSpacing: "-0.03em", color: "var(--text-primary)", textShadow: "0 4px 20px rgba(0,0,0,0.5)" }}>
                  Ready to register lunar imagery?
                </h2>
              </motion.div>
              <p style={{ color: "var(--text-secondary)", marginBottom: 44, fontSize: 16, maxWidth: 540, margin: "0 auto 44px", lineHeight: 1.8 }}>
                Upload your source and reference images. SELORA handles the rest with precision and confidence.
              </p>
              <Link href="/workspace">
                <motion.button 
                  whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(0,200,255,0.6)" }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-hero-primary" 
                  style={{ fontSize: 16, padding: "16px 36px" }}
                >
                  Open Workspace <ChevronRight size={18} />
                </motion.button>
              </Link>
            </div>
          </motion.div>
        </section>

        {/* ── Footer ── */}
        <motion.footer 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-footer" 
          style={{ textAlign: "center", padding: "2rem", background: "rgba(8, 10, 13, 0.9)" }}
        >
          <div style={{ fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.02em" }}>
            Bringing Lunar Perspectives
          </div>
        </motion.footer>
      </div>
    </div>
  );
}
