import { useState } from "react";
import { analyzeCracks, validateImageFile } from "../services/api";
import ImageUploader from "../components/ImageUploader";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

const SEVERITY_COLOR = {
  none: "#16a34a",
  hairline: "#65a30d",
  minor: "#d97706",
  moderate: "#ea580c",
  severe: "#dc2626",
  critical: "#7c3aed",
};

export default function CrackDetection({ backendStatus }) {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    const validationError = validateImageFile(file);
    if (validationError) { setError(validationError); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await analyzeCracks(file, context));
    } catch (err) {
      setError(err.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feature-panel">
      <form onSubmit={handleSubmit} className="feature-form">
        <ImageUploader file={file} onChange={(f) => { setFile(f); setResult(null); setError(""); }} />

        <div className="form-group">
          <label>Additional context (optional)</label>
          <textarea
            placeholder="e.g. External wall, 10-year-old concrete structure, basement level"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={3}
          />
        </div>

        <button
          className="btn-primary"
          type="submit"
          disabled={loading || !file || backendStatus !== "healthy"}
        >
          {loading ? <><Spinner /> Analyzing...</> : "Detect Cracks"}
        </button>
        {backendStatus !== "healthy" && (
          <p className="hint-text">Backend unavailable — cannot run analysis.</p>
        )}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div className="risk-banner" style={{ background: result.crack_detected ? "#fff1f2" : "#f0fdf4" }}>
            <span
              className="risk-badge"
              style={{ background: SEVERITY_COLOR[result.overall_severity] || "#64748b" }}
            >
              {result.crack_detected ? "CRACKS DETECTED" : "NO CRACKS DETECTED"}
            </span>
            <span className="ppe-badge">Structural risk: {result.structural_risk}</span>
            {result.immediate_action_required && (
              <span className="risk-badge" style={{ background: "#dc2626" }}>⚠ IMMEDIATE ACTION REQUIRED</span>
            )}
          </div>

          <p className="result-summary">{result.summary}</p>

          {result.cracks?.length > 0 && (
            <ResultCard title={`🔍 Crack Analysis (${result.cracks.length} found)`}>
              <div className="hazard-list">
                {result.cracks.map((c, i) => (
                  <div key={i} className="hazard-item">
                    <div className="hazard-header">
                      <span className="hazard-type">{c.type}</span>
                      <span className="severity-tag" style={{ color: SEVERITY_COLOR[c.severity] || "#64748b" }}>
                        {c.severity}
                      </span>
                    </div>
                    <p className="hazard-location">📍 {c.location}</p>
                    <p className="hazard-desc">🔎 Probable cause: {c.probable_cause}</p>
                    <p className="hazard-rec">✅ {c.recommended_action}</p>
                  </div>
                ))}
              </div>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  );
}
