"use client";

import { useState } from "react";
import Link from "next/link";
import { Satellite, ArrowLeft, Play, Loader2, BarChart3, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { uploadImage, uploadPreset, runBenchmark, imageUrl } from "@/lib/api";
import type { BenchmarkResult } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";

const METHODS = ["orb", "sift", "akaze", "deep", "loftr", "selora_same", "selora_cross"];

const METHOD_META: Record<string, { color: string; desc: string }> = {
  ORB: { color: "#f59e0b", desc: "Fast binary descriptor" },
  SIFT: { color: "#3b82f6", desc: "Scale-invariant float descriptor" },
  AKAZE: { color: "#8b5cf6", desc: "Nonlinear scale space" },
  DEEP: { color: "#ec4899", desc: "PyTorch SuperPoint (Kornia)" },
  LOFTR: { color: "#a855f7", desc: "Learned detector-free matcher (Kornia)" },
  SELORA_SAME: { color: "#00c8ff", desc: "Sensor-aware (gradient off)" },
  SELORA_CROSS: { color: "#10b981", desc: "Sensor-aware (gradient on)" },
  SELORA: { color: "#00c8ff", desc: "Sensor-aware full pipeline" },
  SELORA_same: { color: "#00c8ff", desc: "Sensor-aware (gradient off)" },
  SELORA_cross: { color: "#10b981", desc: "Sensor-aware (gradient on)" },
};

const PRESET_OPTIONS = [
  {
    id: "same_sensor",
    label: "Same-Sensor (Easy)",
    source: "demo_same_source.png",
    reference: "demo_same_reference.png",
    description: "Same sensor, 5° rotation. Standard case.",
    difficulty: "easy",
    difficultyBadge: "EASY",
    difficultyColor: "var(--success)",
  },
  {
    id: "cross_sensor",
    label: "Cross-Sensor OHRC→TMC2 (Hard)",
    source: "demo_ohrc_source.png",
    reference: "demo_tmc2_reference.png",
    description: "20:1 scale ratio. Cross-modal simulation.",
    difficulty: "hard",
    difficultyBadge: "HARD",
    difficultyColor: "var(--warning)",
  },
  {
    id: "extreme_illum",
    label: "Extreme Illumination (Very Hard)",
    source: "demo_hard_source.png",
    reference: "demo_hard_reference.png",
    description: "15° rotation, 40-intensity brightness shift.",
    difficulty: "very_hard",
    difficultyBadge: "VERY HARD",
    difficultyColor: "var(--error)",
  },
  {
    id: "custom",
    label: "Custom Upload",
    source: "",
    reference: "",
    description: "Upload your own lunar image pair.",
    difficulty: "custom",
    difficultyBadge: "CUSTOM",
    difficultyColor: "var(--accent-cyan)",
  },
];

export default function BenchmarkPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>("same_sensor");
  const [srcFile, setSrcFile] = useState<File | null>(null);
  const [refFile, setRefFile] = useState<File | null>(null);
  const [result, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      let srcId = "";
      let refId = "";

      if (selectedPreset === "custom") {
        if (!srcFile || !refFile) {
          setError("Please select both source and reference images.");
          setLoading(false);
          return;
        }
        const [srcInfo, refInfo] = await Promise.all([
          uploadImage(srcFile, "auto"),
          uploadImage(refFile, "auto"),
        ]);
        srcId = srcInfo.image_id;
        refId = refInfo.image_id;
      } else {
        const pData = await uploadPreset(selectedPreset);
        srcId = pData.source_image_id;
        refId = pData.reference_image_id;
      }

      const bResult = await runBenchmark({
        source_image_id: srcId,
        reference_image_id: refId,
        methods: METHODS,
      });
      setBenchmarkResult(bResult);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const best = result?.rows.reduce((a, b) => (b.confidence > a.confidence ? b : a), result.rows[0]);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-surface)",
          padding: "0 2rem",
          height: 56,
          display: "flex",
          alignItems: "center",
          gap: 16,
          position: "sticky",
          top: 0,
          zIndex: 40,
        }}
      >
        <Link href="/">
          <button className="btn-secondary" style={{ padding: "0.4rem 0.75rem" }}>
            <ArrowLeft size={14} /> Home
          </button>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <BarChart3 size={16} color="var(--accent-cyan)" />
          <span style={{ fontWeight: 700, fontSize: 14 }}>Method Benchmark</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/benchmark/compare">
            <button className="btn-primary" style={{ padding: "0.4rem 0.85rem", fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <TrendingUp size={14} /> View Full Matrix
            </button>
          </Link>
          <span className="badge badge-cyan">Research Mode</span>
        </div>
      </header>

      <motion.main 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem" }}
      >
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          style={{ marginBottom: 24 }}
        >
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: 8 }}>
            Algorithm Comparison
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Compare ORB, SIFT, AKAZE, DEEP, LoFTR, and SELORA on the same image pair with real computed metrics.
          </p>
          <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.3)", borderRadius: "var(--radius)", fontSize: 12, color: "#c084fc", display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span>⚡ Note: LoFTR runs slowly on CPU (~20-60s per pair).</span>
          </div>
        </motion.div>

        {/* Preset Selector & Upload zone */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="selora-card" 
          style={{ marginBottom: 24, background: "rgba(22, 28, 38, 0.7)", backdropFilter: "blur(12px)", border: "1px solid rgba(0, 200, 255, 0.1)" }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div className="text-label">Evaluation Benchmark Pair</div>
            <Link href="/benchmark/compare">
              <button className="btn-secondary" style={{ padding: "0.35rem 0.75rem", fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <TrendingUp size={13} color="var(--accent-cyan)" /> Run All Presets Matrix
              </button>
            </Link>
          </div>

          {/* Preset Buttons */}
          <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600, marginRight: 4 }}>
              Presets:
            </span>
            {PRESET_OPTIONS.map((p) => {
              const active = selectedPreset === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedPreset(p.id)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "var(--radius)",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    background: active ? "rgba(0, 200, 255, 0.15)" : "var(--bg-elevated)",
                    color: active ? "var(--accent-cyan)" : "var(--text-secondary)",
                    border: active ? "1px solid var(--accent-cyan)" : "1px solid var(--border)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {selectedPreset !== "custom" ? (
            /* Read-only Preset Display */
            (() => {
              const currentPreset = PRESET_OPTIONS.find((p) => p.id === selectedPreset)!;
              return (
                <div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 200px",
                      gap: 16,
                      alignItems: "center",
                      background: "var(--bg-elevated)",
                      padding: "14px 16px",
                      borderRadius: "var(--radius)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Source Preset File</div>
                      <div style={{ fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: "var(--accent-cyan)" }}>
                        {currentPreset.source}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Reference Preset File</div>
                      <div style={{ fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: "var(--accent-cyan)" }}>
                        {currentPreset.reference}
                      </div>
                    </div>
                    <div>
                      <button
                        className="btn-primary"
                        onClick={handleRun}
                        disabled={loading}
                        style={{ width: "100%", justifyContent: "center" }}
                      >
                        {loading ? <><Loader2 size={15} className="spin" /> Benchmarking...</> : <><Play size={15} /> Run Benchmark</>}
                      </button>
                    </div>
                  </div>
                  <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 10, alignItems: "center" }}>
                    <span className="badge" style={{ borderColor: currentPreset.difficultyColor, color: currentPreset.difficultyColor }}>
                      {currentPreset.difficultyBadge}
                    </span>
                    <span>{currentPreset.description}</span>
                  </div>
                </div>
              );
            })()
          ) : (
            /* Custom Upload Inputs */
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 200px", gap: 16, alignItems: "end" }}>
              <div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>Source Image</div>
                <label
                  style={{
                    display: "block",
                    padding: "10px 14px",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    cursor: "pointer",
                    fontSize: 13,
                    color: srcFile ? "var(--success)" : "var(--text-muted)",
                  }}
                >
                  {srcFile ? srcFile.name : "Click to upload..."}
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.tiff,.tif"
                    style={{ display: "none" }}
                    onChange={(e) => e.target.files?.[0] && setSrcFile(e.target.files[0])}
                  />
                </label>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>Reference Image</div>
                <label
                  style={{
                    display: "block",
                    padding: "10px 14px",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    cursor: "pointer",
                    fontSize: 13,
                    color: refFile ? "var(--success)" : "var(--text-muted)",
                  }}
                >
                  {refFile ? refFile.name : "Click to upload..."}
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.tiff,.tif"
                    style={{ display: "none" }}
                    onChange={(e) => e.target.files?.[0] && setRefFile(e.target.files[0])}
                  />
                </label>
              </div>
              <button
                className="btn-primary"
                disabled={!srcFile || !refFile || loading}
                onClick={handleRun}
                style={{ width: "100%", justifyContent: "center" }}
              >
                {loading ? <><Loader2 size={15} className="spin" /> Benchmarking...</> : <><Play size={15} /> Run Benchmark</>}
              </button>
            </div>
          )}

          {error && (
            <div style={{ marginTop: 12, color: "var(--error)", fontSize: 13 }}>{error}</div>
          )}
        </motion.div>

        {/* Results table */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, staggerChildren: 0.1 }}
          >
            <div className="selora-card" style={{ marginBottom: 20, border: "1px solid rgba(0, 200, 255, 0.2)", boxShadow: "0 10px 40px rgba(0,0,0,0.2)" }}>
              <div className="text-label" style={{ marginBottom: 16 }}>Benchmark Results</div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["Method", "Matches", "Inliers", "Inlier Ratio", "RMSE", "Coverage", "Confidence", "Time"].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 12px",
                            textAlign: h === "Method" ? "left" : "right",
                            fontSize: 11,
                            fontWeight: 600,
                            letterSpacing: "0.06em",
                            textTransform: "uppercase",
                            color: "var(--text-muted)",
                            borderBottom: "1px solid var(--border)",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row) => {
                      const isBest = row === best;
                      const meta = METHOD_META[row.method] ?? { color: "var(--text-primary)", desc: "" };
                      return (
                        <tr
                          key={row.method}
                          style={{
                            background: isBest ? "rgba(0,200,255,0.04)" : "transparent",
                          }}
                        >
                          <td style={{ padding: "10px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div
                                style={{
                                  width: 8, height: 8,
                                  borderRadius: "50%",
                                  background: meta.color,
                                }}
                              />
                              <span style={{ fontWeight: 700, color: isBest ? "var(--accent-cyan)" : "var(--text-primary)" }}>
                                {row.method}
                              </span>
                              {isBest && <span className="badge badge-cyan" style={{ fontSize: 9 }}>BEST</span>}
                            </div>
                          </td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>{row.matches.toLocaleString()}</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "var(--success)" }}>{row.inliers.toLocaleString()}</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>{(row.inlier_ratio * 100).toFixed(1)}%</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: row.rmse < 5 ? "var(--success)" : row.rmse < 10 ? "var(--warning)" : "var(--error)" }}>{row.rmse === 999 ? "—" : `${row.rmse.toFixed(2)} px`}</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>{(row.coverage * 100).toFixed(1)}%</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "var(--accent-cyan)", fontWeight: 700 }}>{(row.confidence * 100).toFixed(1)}%</td>
                          <td style={{ padding: "10px 12px", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "var(--text-muted)" }}>{row.processing_time_sec.toFixed(2)}s</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>
                * All values are computed from the actual registration pipeline. No hardcoded metrics.
              </div>
            </div>

            {/* Bar chart */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
              }}
            >
              <div className="selora-card" style={{ height: 300 }}>
                <div className="text-label" style={{ marginBottom: 14 }}>Inlier Ratio (%)</div>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.rows.map(r => ({ name: r.method, value: Number((r.inlier_ratio * 100).toFixed(1)), color: METHOD_META[r.method]?.color ?? "#888" }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)' }}
                      cursor={{ fill: 'var(--bg-surface)' }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {result.rows.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={METHOD_META[entry.method]?.color ?? "#888"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="selora-card" style={{ height: 300 }}>
                <div className="text-label" style={{ marginBottom: 14 }}>Processing Time (s)</div>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.rows.map(r => ({ name: r.method, value: Number(r.processing_time_sec.toFixed(2)), color: METHOD_META[r.method]?.color ?? "#888" }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-primary)' }}
                      cursor={{ fill: 'var(--bg-surface)' }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {result.rows.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={METHOD_META[entry.method]?.color ?? "#888"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </motion.div>
        )}

        {!result && !loading && (
          <div
            style={{
              padding: 60,
              textAlign: "center",
              color: "var(--text-muted)",
            }}
          >
            <BarChart3 size={40} style={{ margin: "0 auto 12px", opacity: 0.3 }} />
            <div>Upload an image pair and run the benchmark to compare methods.</div>
          </div>
        )}
      </motion.main>
    </div>
  );
}


