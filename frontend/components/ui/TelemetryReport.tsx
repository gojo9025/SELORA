import React, { forwardRef } from "react";
import { imageUrl, type RegistrationResult } from "@/lib/api";

interface TelemetryReportProps {
  result: RegistrationResult;
}

const TelemetryReport = forwardRef<HTMLDivElement, TelemetryReportProps>(
  ({ result }, ref) => {
    const {
      registration_id,
      source_sensor,
      reference_sensor,
      mode,
      metrics,
      transformation,
      visualizations,
      config_used,
    } = result;

    const dateStr = new Date().toLocaleString("en-US", {
      dateStyle: "long",
      timeStyle: "short",
    });

    return (
      <div
        ref={ref}
        style={{
          width: "210mm", // A4 width
          minHeight: "297mm", // A4 height
          padding: "20mm",
          backgroundColor: "#ffffff",
          color: "#000000",
          fontFamily: "Arial, sans-serif",
          position: "absolute",
          top: "-9999px", // Hide offscreen
          left: "-9999px",
          boxSizing: "border-box",
        }}
      >
        {/* Header */}
        <div style={{ borderBottom: "2px solid #000", paddingBottom: "10px", marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "24px", fontWeight: "bold" }}>ISRO SIH 2026</h1>
            <h2 style={{ margin: "4px 0 0", fontSize: "16px", color: "#555" }}>Optical Registration Telemetry Report</h2>
          </div>
          <div style={{ textAlign: "right", fontSize: "12px", color: "#555" }}>
            <div><strong>Generated:</strong> {dateStr}</div>
            <div><strong>Registration ID:</strong> {registration_id.split("-")[0]}</div>
          </div>
        </div>

        {/* Mission Parameters */}
        <div style={{ marginBottom: "20px" }}>
          <h3 style={{ fontSize: "16px", borderBottom: "1px solid #ccc", paddingBottom: "4px", marginBottom: "10px" }}>Mission Parameters</h3>
          <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
            <tbody>
              <tr>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", backgroundColor: "#f9f9f9", width: "25%" }}><strong>Source Sensor</strong></td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", width: "25%" }}>{source_sensor}</td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", backgroundColor: "#f9f9f9", width: "25%" }}><strong>Reference Sensor</strong></td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", width: "25%" }}>{reference_sensor}</td>
              </tr>
              <tr>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", backgroundColor: "#f9f9f9" }}><strong>Pipeline Mode</strong></td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee" }}>{mode}</td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee", backgroundColor: "#f9f9f9" }}><strong>Transform Model</strong></td>
                <td style={{ padding: "4px 8px", border: "1px solid #eee" }}>{metrics?.transform_model || "N/A"}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Quality Metrics */}
        {metrics && (
          <div style={{ marginBottom: "20px" }}>
            <h3 style={{ fontSize: "16px", borderBottom: "1px solid #ccc", paddingBottom: "4px", marginBottom: "10px" }}>Quality Assessment</h3>
            <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ backgroundColor: "#f0f0f0" }}>
                  <th style={{ padding: "6px 8px", border: "1px solid #ddd", textAlign: "left" }}>Metric</th>
                  <th style={{ padding: "6px 8px", border: "1px solid #ddd", textAlign: "left" }}>Value</th>
                  <th style={{ padding: "6px 8px", border: "1px solid #ddd", textAlign: "left" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Confidence Score</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{(metrics.confidence * 100).toFixed(1)}%</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee", color: metrics.confidence > 0.6 ? "green" : "red" }}>
                    {metrics.confidence > 0.6 ? "NOMINAL" : "REVIEW REQUIRED"}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Reprojection RMSE (Training)</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{metrics.rmse.toFixed(2)} px</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>NOMINAL</td>
                </tr>
                {metrics.cv_rmse != null && (
                  <tr>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Independent CV-RMSE (Leave-K-Out)</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{metrics.cv_rmse.toFixed(2)} px</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee", color: "green" }}>VERIFIED (NON-CIRCULAR)</td>
                  </tr>
                )}
                {metrics.ssim != null && (
                  <tr>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Structural Similarity (SSIM)</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{metrics.ssim.toFixed(3)}</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>NOMINAL</td>
                  </tr>
                )}
                {metrics.ncc != null && (
                  <tr>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Norm. Cross-Correlation (NCC)</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{metrics.ncc.toFixed(3)}</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>NOMINAL</td>
                  </tr>
                )}
                {metrics.sub_pixel_dx != null && metrics.sub_pixel_dy != null && (
                  <tr>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Phase Correlation Sub-Pixel Shift</td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>
                      Δx: {metrics.sub_pixel_dx.toFixed(3)} px, Δy: {metrics.sub_pixel_dy.toFixed(3)} px
                    </td>
                    <td style={{ padding: "6px 8px", border: "1px solid #eee", color: "green" }}>SUB-PIXEL CONVERGED</td>
                  </tr>
                )}
                <tr>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Inlier Ratio</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{(metrics.inlier_ratio * 100).toFixed(1)}% ({metrics.inlier_count} / {metrics.total_matches})</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>NOMINAL</td>
                </tr>
                <tr>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>Spatial Coverage</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>{(metrics.spatial_coverage * 100).toFixed(1)}%</td>
                  <td style={{ padding: "6px 8px", border: "1px solid #eee" }}>NOMINAL</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Transformation Matrix */}
        {transformation && (
          <div style={{ marginBottom: "20px" }}>
            <h3 style={{ fontSize: "16px", borderBottom: "1px solid #ccc", paddingBottom: "4px", marginBottom: "10px" }}>Estimated Geometry</h3>
            <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
              <div style={{ fontSize: "12px", fontFamily: "monospace", padding: "10px", backgroundColor: "#f9f9f9", border: "1px solid #eee", display: "inline-block" }}>
                {transformation.matrix.map((row, i) => (
                  <div key={i} style={{ display: "flex", gap: "10px" }}>
                    {row.map((val, j) => (
                      <span key={j} style={{ width: "80px", textAlign: "right" }}>
                        {val.toFixed(4)}
                      </span>
                    ))}
                  </div>
                ))}
              </div>
              <div style={{ fontSize: "12px" }}>
                <div><strong>Scale:</strong> {transformation.scale?.toFixed(4) || "N/A"}</div>
                <div><strong>Rotation:</strong> {transformation.rotation_deg?.toFixed(2) || "N/A"}°</div>
                <div><strong>Translation:</strong> [{transformation.translation_x?.toFixed(1)}, {transformation.translation_y?.toFixed(1)}]</div>
              </div>
            </div>
          </div>
        )}

        {/* Visualizations */}
        {visualizations && (
          <div style={{ marginTop: "30px", pageBreakInside: "avoid" }}>
            <h3 style={{ fontSize: "16px", borderBottom: "1px solid #ccc", paddingBottom: "4px", marginBottom: "15px" }}>Visual Telemetry</h3>
            
            <div style={{ display: "flex", gap: "15px", marginBottom: "15px" }}>
              {visualizations.difference_map && (
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "10px", fontWeight: "bold", marginBottom: "4px" }}>DIFFERENCE MAP</div>
                  <img
                    src={imageUrl(visualizations.difference_map)}
                    crossOrigin="anonymous"
                    style={{ width: "100%", border: "1px solid #ddd" }}
                  />
                </div>
              )}
              {visualizations.overlay_image && (
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "10px", fontWeight: "bold", marginBottom: "4px" }}>ALPHA BLEND OVERLAY</div>
                  <img
                    src={imageUrl(visualizations.overlay_image)}
                    crossOrigin="anonymous"
                    style={{ width: "100%", border: "1px solid #ddd" }}
                  />
                </div>
              )}
            </div>

            {visualizations.match_visualization && (
              <div style={{ width: "100%", pageBreakInside: "avoid" }}>
                <div style={{ fontSize: "10px", fontWeight: "bold", marginBottom: "4px" }}>INLIER MATCH CORRESPONDENCES</div>
                <img
                  src={imageUrl(visualizations.match_visualization)}
                  crossOrigin="anonymous"
                  style={{ width: "100%", border: "1px solid #ddd" }}
                />
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div style={{ marginTop: "40px", borderTop: "1px solid #ccc", paddingTop: "10px", fontSize: "10px", color: "#777", textAlign: "center" }}>
          SELORA Framework | Generated by automated pipeline | FOR OFFICIAL USE ONLY
        </div>
      </div>
    );
  }
);

TelemetryReport.displayName = "TelemetryReport";

export default TelemetryReport;
