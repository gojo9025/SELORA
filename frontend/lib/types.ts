/**
 * SELORA Shared TypeScript types
 */

export type SensorType = "OHRC" | "TMC2" | "IIRS" | "LRO_NAC" | "SELENE" | "Unknown" | "auto";
export type RegistrationMode = "fast" | "robust" | "research" | "deep" | "auto";

export interface UploadedImage {
  imageId: string;
  filename: string;
  width: number;
  height: number;
  sensor: SensorType;
  previewUrl: string;       // Object URL for client-side preview
}

export type ProcessingStage =
  | "idle"
  | "uploading"
  | "analyzing"
  | "detecting_sensor"
  | "normalizing"
  | "extracting_features"
  | "matching"
  | "geometric_verification"
  | "warping"
  | "evaluating"
  | "complete"
  | "failed";

export const STAGE_LABELS: Record<ProcessingStage, string> = {
  idle: "Ready",
  uploading: "Uploading images...",
  analyzing: "Analyzing images",
  detecting_sensor: "Detecting sensor type",
  normalizing: "Normalizing intensities",
  extracting_features: "Extracting features",
  matching: "Matching correspondences",
  geometric_verification: "Geometric verification (RANSAC)",
  warping: "Warping & aligning",
  evaluating: "Evaluating quality",
  complete: "Registration complete",
  failed: "Registration failed",
};

export const SENSOR_OPTIONS: { value: SensorType; label: string; description: string }[] = [
  { value: "auto", label: "Auto Detect", description: "Automatically infer sensor" },
  { value: "OHRC", label: "OHRC", description: "Orbiter High Resolution Camera (~25cm)" },
  { value: "TMC2", label: "TMC-2", description: "Terrain Mapping Camera 2 (~5m)" },
  { value: "IIRS", label: "IIRS", description: "Imaging IR Spectrometer (~80m)" },
  { value: "LRO_NAC", label: "LRO NAC", description: "Lunar Reconnaissance Orbiter Narrow Angle Camera (~0.5m)" },
  { value: "SELENE", label: "SELENE (Kaguya)", description: "Terrain Camera (~10m)" },
  { value: "Unknown", label: "Other / Unknown", description: "Generic robust pipeline" },
];

export const MODE_OPTIONS: { value: RegistrationMode; label: string; description: string; badge: string }[] = [
  { value: "auto", label: "AUTO", description: "Sensor-adaptive pipeline selection", badge: "Recommended" },
  { value: "fast", label: "FAST", description: "ORB + BFMatcher, < 5 seconds", badge: "" },
  { value: "robust", label: "ROBUST", description: "SIFT + multi-scale + mutual matching", badge: "Default" },
  { value: "research", label: "RESEARCH", description: "Full pipeline, all metrics, < 60s", badge: "Advanced" },
  { value: "deep", label: "DEEP", description: "PyTorch SuperPoint (Kornia)", badge: "AI" },
];

