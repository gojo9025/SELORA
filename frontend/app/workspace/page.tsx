"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Satellite, Upload, ChevronDown, Settings, AlertCircle,
  Loader2, Play, ArrowLeft, Info,
} from "lucide-react";
import { useEffect } from "react";
import { uploadImage, registerImages, getRegistrations, imageUrl } from "@/lib/api";
import type { SensorType, RegistrationMode, RegistrationResult } from "@/lib/api";
import { SENSOR_OPTIONS, MODE_OPTIONS, STAGE_LABELS, type ProcessingStage } from "@/lib/types";
import { motion, AnimatePresence } from 'framer-motion';
import FloatingSpaceAssets from "@/components/ui/FloatingSpaceAssets";

interface DroppedImage {
  file: File;
  previewUrl: string;
  imageId: string;
  sensor: SensorType;
  width: number;
  height: number;
}

const ORDERED_STAGES: ProcessingStage[] = [
  "analyzing", "detecting_sensor", "normalizing",
  "extracting_features", "matching", "geometric_verification",
  "warping", "evaluating",
];

export default function WorkspacePage() {
  const router = useRouter();
  const srcInputRef = useRef<HTMLInputElement>(null);
  const refInputRef = useRef<HTMLInputElement>(null);

  const [source, setSource] = useState<DroppedImage | null>(null);
  const [reference, setReference] = useState<DroppedImage | null>(null);
  const [srcSensor, setSrcSensor] = useState<SensorType>("auto");
  const [refSensor, setRefSensor] = useState<SensorType>("auto");
  const [mode, setMode] = useState<RegistrationMode>("auto");
  const [stage, setStage] = useState<ProcessingStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [srcDragging, setSrcDragging] = useState(false);
  const [refDragging, setRefDragging] = useState(false);

  const [history, setHistory] = useState<RegistrationResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await getRegistrations();
        setHistory(data);
      } catch (err) {
        console.error("Failed to load history:", err);
      } finally {
        setHistoryLoading(false);
      }
    }
    loadHistory();
  }, []);

  const handleFile = useCallback(
    async (file: File, role: "source" | "reference", sensor: SensorType = "auto") => {
      if (!file) return;
      const previewUrl = URL.createObjectURL(file);
      try {
        setStage("uploading" as ProcessingStage);
        setError(null);
        const info = await uploadImage(file, sensor);
        const img: DroppedImage = {
          file,
          previewUrl,
          imageId: info.image_id,
          sensor: (info.sensor as SensorType) || "Unknown",
          width: info.width,
          height: info.height,
        };
        if (role === "source") {
          setSource(img);
          if (info.sensor && info.sensor !== "Unknown") setSrcSensor(info.sensor as SensorType);
        } else {
          setReference(img);
          if (info.sensor && info.sensor !== "Unknown") setRefSensor(info.sensor as SensorType);
        }
      } catch (err: unknown) {
        setError(`Upload failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setStage("idle");
      }
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent, role: "source" | "reference") => {
      e.preventDefault();
      if (role === "source") setSrcDragging(false);
      else setRefDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file, role);
    },
    [handleFile]
  );

  const simulateStages = async (regId: string) => {
    for (const s of ORDERED_STAGES) {
      setStage(s);
      await new Promise((r) => setTimeout(r, 600));
    }
  };

  const handleRegister = async () => {
    if (!source || !reference) return;
    setError(null);
    setStage("analyzing");

    try {
      // Simulate stage animation then do real API call
      const stagePromise = simulateStages("tmp");
      const apiPromise = registerImages({
        source_image_id: source.imageId,
        reference_image_id: reference.imageId,
        source_sensor: srcSensor,
        reference_sensor: refSensor,
        mode,
      });

      const [, result] = await Promise.all([stagePromise, apiPromise]);

      setStage("complete");
      router.push(`/results/${result.registration_id}`);
    } catch (err: unknown) {
      setStage("failed");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const isProcessing = stage !== "idle" && stage !== "complete" && stage !== "failed";
  const canRegister = source && reference && !isProcessing;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)", display: "flex", flexDirection: "column", position: "relative" }}>
      <FloatingSpaceAssets />
      {/* ── Header ── */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-surface)",
          padding: "0 2rem",
          height: 56,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/">
            <button className="btn-secondary" style={{ padding: "0.4rem 0.75rem" }}>
              <ArrowLeft size={14} /> Back
            </button>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Satellite size={16} color="var(--accent-cyan)" />
            <span style={{ fontWeight: 700, fontSize: 14 }}>SELORA Workspace</span>
          </div>
        </div>
        <Link href="/benchmark">
          <button className="btn-secondary" style={{ padding: "0.4rem 0.75rem", fontSize: 12 }}>
            <Settings size={13} /> Benchmark
          </button>
        </Link>
      </header>

      <main style={{ flex: 1, maxWidth: 1200, width: "100%", margin: "0 auto", padding: "2rem", position: "relative", zIndex: 10 }}>
        {/* ── Error Banner ── */}
        {error && (
          <div
            style={{
              background: "var(--error-bg)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "var(--radius)",
              padding: "12px 16px",
              marginBottom: 20,
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
            }}
          >
            <AlertCircle size={16} color="var(--error)" style={{ marginTop: 2, flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 600, color: "var(--error)", fontSize: 13 }}>Registration Error</div>
              <div style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 2 }}>{error}</div>
            </div>
          </div>
        )}

        {/* ── Upload Zone ── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 20,
            marginBottom: 24,
          }}
        >
          {/* Source */}
          <ImageDropZone
            label="Source Image"
            role="source"
            image={source}
            dragging={srcDragging}
            inputRef={srcInputRef}
            onDragOver={(e) => { e.preventDefault(); setSrcDragging(true); }}
            onDragLeave={() => setSrcDragging(false)}
            onDrop={(e) => handleDrop(e, "source")}
            onFileChange={(f) => handleFile(f, "source")}
            sensor={srcSensor}
            onSensorChange={setSrcSensor}
          />

          {/* Reference */}
          <ImageDropZone
            label="Reference Image"
            role="reference"
            image={reference}
            dragging={refDragging}
            inputRef={refInputRef}
            onDragOver={(e) => { e.preventDefault(); setRefDragging(true); }}
            onDragLeave={() => setRefDragging(false)}
            onDrop={(e) => handleDrop(e, "reference")}
            onFileChange={(f) => handleFile(f, "reference")}
            sensor={refSensor}
            onSensorChange={setRefSensor}
          />
        </div>

        {/* ── Configuration ── */}
        <div
          className="selora-card"
          style={{ marginBottom: 24, display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}
        >
          <div style={{ flex: 1, minWidth: 200 }}>
            <div className="text-label" style={{ marginBottom: 8 }}>Registration Mode</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {MODE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setMode(opt.value)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "var(--radius)",
                    border: `1px solid ${mode === opt.value ? "var(--accent-cyan)" : "var(--border)"}`,
                    background: mode === opt.value ? "var(--accent-cyan-glow)" : "var(--bg-elevated)",
                    color: mode === opt.value ? "var(--accent-cyan)" : "var(--text-secondary)",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  {opt.label}
                  {opt.badge && (
                    <span
                      className="badge badge-cyan"
                      style={{ marginLeft: 6, fontSize: 9 }}
                    >
                      {opt.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
              {MODE_OPTIONS.find((o) => o.value === mode)?.description}
            </div>
          </div>

          {/* Register button */}
          <button
            className="btn-primary"
            style={{ padding: "1rem 2.5rem", fontSize: 14, minWidth: 200 }}
            onClick={handleRegister}
            disabled={!canRegister}
          >
            {isProcessing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play size={16} />
                Register Images
              </>
            )}
          </button>
        </div>

        {/* ── Processing Progress ── */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div 
              className="selora-card"
              initial={{ opacity: 0, height: 0, overflow: 'hidden' }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="text-label" style={{ marginBottom: 16 }}>Pipeline Progress</div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 8,
              }}
            >
              {ORDERED_STAGES.map((s) => {
                const currentIdx = ORDERED_STAGES.indexOf(stage as ProcessingStage);
                const thisIdx = ORDERED_STAGES.indexOf(s);
                const isDone = thisIdx < currentIdx;
                const isActive = s === stage;
                return (
                  <div
                    key={s}
                    className={`pipeline-stage ${isDone ? "done" : isActive ? "active" : "pending"}`}
                  >
                    <div
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: isDone
                          ? "var(--success)"
                          : isActive
                          ? "var(--accent-cyan)"
                          : "var(--border)",
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 11,
                        color: isDone
                          ? "var(--success)"
                          : isActive
                          ? "var(--accent-cyan)"
                          : "var(--text-muted)",
                        fontWeight: isActive ? 600 : 400,
                      }}
                    >
                      {STAGE_LABELS[s]}
                    </span>
                  </div>
                );
              })}
            </div>
              <motion.div 
                className="progress-bar" 
                style={{ marginTop: 16 }}
              >
                <motion.div
                  className="progress-fill"
                  initial={{ width: 0 }}
                  animate={{
                    width: `${((ORDERED_STAGES.indexOf(stage as ProcessingStage) + 1) / ORDERED_STAGES.length) * 100}%`,
                  }}
                  transition={{ duration: 0.5 }}
                />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Historical Dashboard ── */}
        {!isProcessing && !source && !reference && (
          <div style={{ marginTop: 40 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Registration History
              </h2>
            </div>
            {historyLoading ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)" }}>
                <Loader2 size={16} className="animate-spin" />
                <span>Loading history...</span>
              </div>
            ) : history.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", background: "var(--bg-surface)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)" }}>
                <div style={{ color: "var(--text-muted)" }}>No registrations found. Upload images above to get started.</div>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
                {history.map((reg) => (
                  <Link href={`/results/${reg.registration_id}`} key={reg.registration_id} style={{ textDecoration: "none" }}>
                    <div className="selora-card" style={{ padding: 16, cursor: "pointer", transition: "transform 0.1s, border-color 0.1s", ':hover': { transform: "translateY(-2px)", borderColor: "var(--accent-cyan)" } } as any}>
                      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img 
                          src={reg.visualizations?.source_thumbnail ? imageUrl(reg.visualizations.source_thumbnail) : "/placeholder.jpg"} 
                          style={{ width: 60, height: 60, borderRadius: 6, objectFit: "cover", background: "var(--bg-elevated)" }} 
                          alt="Source"
                        />
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img 
                          src={reg.visualizations?.reference_thumbnail ? imageUrl(reg.visualizations.reference_thumbnail) : "/placeholder.jpg"} 
                          style={{ width: 60, height: 60, borderRadius: 6, objectFit: "cover", background: "var(--bg-elevated)" }} 
                          alt="Reference"
                        />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{reg.source_sensor} → {reg.reference_sensor}</div>
                          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{new Date(reg.created_at || "").toLocaleString()}</div>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                          {reg.status === "failed" ? (
                            <span className="badge badge-error">Failed</span>
                          ) : (
                            <>
                              <span className="badge badge-cyan">{reg.mode}</span>
                              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--success)" }}>
                                {(reg.metrics?.confidence ? reg.metrics.confidence * 100 : 0).toFixed(1)}%
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tips ── */}
        {!source && !reference && (
          <div
            style={{
              marginTop: 40,
              padding: "24px",
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <Info size={16} color="var(--accent-cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>
                  Getting Started
                </div>
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {[
                    "Upload a SOURCE image (e.g., OHRC high-resolution lunar image)",
                    "Upload a REFERENCE image (e.g., TMC-2 for spatial context)",
                    "Select sensor types — or let SELORA auto-detect from filename",
                    "Choose registration mode (AUTO recommended for first-time use)",
                    "Click Register Images to run the full pipeline",
                  ].map((tip, i) => (
                    <li
                      key={i}
                      style={{
                        display: "flex",
                        gap: 10,
                        marginBottom: 6,
                        color: "var(--text-secondary)",
                        fontSize: 13,
                      }}
                    >
                      <span
                        style={{
                          color: "var(--accent-cyan)",
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 11,
                          minWidth: 18,
                          paddingTop: 2,
                        }}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ImageDropZone Component
// ─────────────────────────────────────────────────────────────────────────────

interface DropZoneProps {
  label: string;
  role: "source" | "reference";
  image: DroppedImage | null;
  dragging: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  onFileChange: (f: File) => void;
  sensor: SensorType;
  onSensorChange: (s: SensorType) => void;
}

function ImageDropZone({
  label, role, image, dragging, inputRef,
  onDragOver, onDragLeave, onDrop, onFileChange,
  sensor, onSensorChange,
}: DropZoneProps) {
  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div>
          <div className="text-label">{label}</div>
          {image && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
              {image.width}×{image.height} · {(image.file.size / 1024 / 1024).toFixed(1)} MB
            </div>
          )}
        </div>
        {image && (
          <span className="badge badge-success">{image.sensor}</span>
        )}
      </div>

      {/* Drop zone */}
      <div
        className={`dropzone ${dragging ? "drag-over" : ""} ${image ? "has-image" : ""}`}
        style={{ height: 280, position: "relative" }}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !image && inputRef.current?.click()}
      >
        {image ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={image.previewUrl}
              alt={label}
              style={{ width: "100%", height: "100%", objectFit: "contain", padding: 8 }}
            />
            <div
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                display: "flex",
                gap: 6,
              }}
            >
              <button
                className="btn-secondary"
                style={{ padding: "4px 8px", fontSize: 11 }}
                onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
              >
                Replace
              </button>
            </div>
            <div className="scan-line" />
          </>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              gap: 12,
              pointerEvents: "none",
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Upload size={22} color="var(--text-muted)" />
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                Drop image here
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                PNG, JPG, TIFF, GeoTIFF
              </div>
            </div>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.tiff,.tif"
          style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileChange(f); }}
        />
      </div>

      {/* Sensor selector */}
      <div style={{ marginTop: 10 }}>
        <div className="text-label" style={{ marginBottom: 6 }}>Sensor Type</div>
        <select
          className="selora-select"
          value={sensor}
          onChange={(e) => onSensorChange(e.target.value as SensorType)}
        >
          {SENSOR_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label} — {opt.description}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
