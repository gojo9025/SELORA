/**
 * SELORA API Client
 * All fetch calls to the FastAPI backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  }
  return `${API_BASE}${path}`;
}

export type SensorType = "OHRC" | "TMC2" | "IIRS" | "LRO_NAC" | "SELENE" | "Unknown" | "auto";
export type RegistrationMode = "fast" | "robust" | "research" | "deep" | "auto";

export interface ImageInfo {
  image_id: string;
  filename: string;
  width: number;
  height: number;
  channels: number;
  dtype: string;
  file_size_bytes: number;
  sensor: string;
  has_geotiff_metadata: boolean;
  created_at: string;
}

export interface RegistrationMetrics {
  total_matches: number;
  inlier_count: number;
  inlier_ratio: number;
  rmse: number;
  median_reprojection_error: number;
  spatial_coverage: number;
  confidence: number;
  processing_time_sec: number;
  transform_model: string;
  pyramid_levels_used: number;
  // Advanced validation metrics
  cv_rmse: number | null;
  ssim: number | null;
  ncc: number | null;
  mutual_information: number | null;
  overlap_fraction: number | null;
  sub_pixel_dx: number | null;
  sub_pixel_dy: number | null;
  sub_pixel_confidence: number | null;
  radiometric_method: string | null;
  relief_method?: string | null;
  source_lat?: number | null;
  source_lon?: number | null;
  reference_lat?: number | null;
  reference_lon?: number | null;
  source_sun_azimuth?: number | null;
  source_sun_elevation?: number | null;
  reference_sun_azimuth?: number | null;
  reference_sun_elevation?: number | null;
  image_orientation?: string | null;
}

export interface TransformationMatrix {
  model: string;
  matrix: number[][];
  rotation_deg: number | null;
  scale: number | null;
  translation_x: number | null;
  translation_y: number | null;
  inlier_count: number;
  reprojection_rmse: number;
  confidence: number;
}

export interface Visualizations {
  registered_image: string;
  overlay_image: string;
  difference_map: string;
  error_heatmap: string;
  match_visualization: string;
  inlier_visualization: string;
  source_thumbnail: string;
  reference_thumbnail: string;
  source_relief?: string | null;
  reference_relief?: string | null;
  counterfactual_render?: string | null;
}

export interface RegistrationResult {
  status: "success" | "failed" | "warning";
  registration_id: string;
  source_image_id: string;
  reference_image_id: string;
  source_sensor: string;
  reference_sensor: string;
  mode: string;
  metrics: RegistrationMetrics | null;
  transformation: TransformationMatrix | null;
  visualizations: Visualizations | null;
  failure_reason: string | null;
  diagnostics?: Record<string, unknown>;
  suggestions?: string[];
  warnings: string[];
  config_used: Record<string, unknown> | null;
  created_at?: string;
}

export interface BenchmarkRow {
  method: string;
  matches: number;
  inliers: number;
  inlier_ratio: number;
  rmse: number;
  processing_time_sec: number;
  coverage: number;
  confidence: number;
}

export interface BenchmarkResult {
  benchmark_id: string;
  rows: BenchmarkRow[];
  created_at: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      if (json.detail) {
        detail = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
      } else {
        detail = JSON.stringify(json);
      }
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function uploadImage(
  file: File,
  sensor: SensorType = "auto"
): Promise<ImageInfo> {
  const form = new FormData();
  form.append("file", file);
  form.append("sensor", sensor);
  const res = await fetch(apiUrl("/api/images/upload"), {
    method: "POST",
    body: form,
  });
  return handleResponse<ImageInfo>(res);
}

export async function getImage(imageId: string): Promise<ImageInfo> {
  const res = await fetch(apiUrl(`/api/images/${imageId}`));
  return handleResponse<ImageInfo>(res);
}

export async function registerImages(params: {
  source_image_id: string;
  reference_image_id: string;
  source_sensor: SensorType;
  reference_sensor: SensorType;
  mode: RegistrationMode;
}): Promise<RegistrationResult> {
  const res = await fetch(apiUrl("/api/register"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return handleResponse<RegistrationResult>(res);
}

export async function getRegistration(regId: string): Promise<RegistrationResult> {
  const res = await fetch(apiUrl(`/api/registration/${regId}`));
  return handleResponse<RegistrationResult>(res);
}

export async function getRegistrations(): Promise<RegistrationResult[]> {
  const res = await fetch(apiUrl("/api/registrations"));
  return handleResponse<RegistrationResult[]>(res);
}

export interface BenchmarkPreset {
  id: string;
  label: string;
  source: string;
  reference: string;
  description: string;
  difficulty: "easy" | "hard" | "very_hard";
}

export async function listPresets(): Promise<{ presets: BenchmarkPreset[] }> {
  const res = await fetch(apiUrl("/api/benchmark/presets"));
  return handleResponse<{ presets: BenchmarkPreset[] }>(res);
}

export async function uploadPreset(presetId: string): Promise<{
  preset_id: string;
  source_image_id: string;
  reference_image_id: string;
  label: string;
  difficulty: string;
}> {
  const res = await fetch(apiUrl("/api/benchmark/upload-preset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset_id: presetId }),
  });
  return handleResponse(res);
}

export async function runBenchmark(params: {
  source_image_id: string;
  reference_image_id: string;
  methods?: string[];
}): Promise<BenchmarkResult> {
  const res = await fetch(apiUrl("/api/benchmark/run"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...params, methods: params.methods ?? ["orb", "sift", "akaze", "deep", "loftr", "selora_same", "selora_cross"] }),
  });
  return handleResponse<BenchmarkResult>(res);
}

export function imageUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return apiUrl(url);
}

export function downloadUrl(regId: string, artifact: string): string {
  return apiUrl(`/api/registration/${regId}/download/${artifact}`);
}
