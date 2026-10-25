import { useState } from "react";
import { analyzeSafety, validateImageFile } from "../services/api";
import ImageUploader from "../components/ImageUploader";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

const SEVERITY_COLOR = {
  low: "#16a34a",
  medium: "#d97706",
  high: "#dc2626",
  critical: "#7c3aed",
};

const RISK_BG = {
  low: "#f0fdf4",
  medium: "#fffbeb",
  high: "#fff1f2",
  critical: "#f5f3ff",
};

export default function SafetyMonitoring({ backendStatus }) {
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
      setResult(await analyzeSafety(file, context));
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
            placeholder="e.g. Residential building, 3rd floor slab work, 15 workers on site"
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
          {loading ? <><Spinner /> Analyzing...</> : "Analyze for Hazards"}
        </button>
        {backendStatus !== "healthy" && (
          <p className="hint-text">Backend unavailable — cannot run analysis.</p>
        )}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div
            className="risk-banner"
            style={{ background: RISK_BG[result.overall_risk_level] || "#f0f6f1" }}
          >
            <span
              className="risk-badge"
              style={{ background: SEVERITY_COLOR[result.overall_risk_level] || "#64748b" }}
            >
              {result.overall_risk_level?.toUpperCase()} RISK
            </span>
            <span className="ppe-badge">PPE: {result.ppe_compliance}</span>
          </div>

          <p className="result-summary">{result.summary}</p>

          {result.immediate_actions?.length > 0 && (
            <ResultCard title="⚡ Immediate Actions Required">
              <ul className="action-list">
                {result.immediate_actions.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </ResultCard>
          )}

          {result.hazards?.length > 0 && (
            <ResultCard title={`🚨 Hazards Detected (${result.hazards.length})`}>
              <div className="hazard-list">
                {result.hazards.map((h, i) => (
                  <div key={i} className="hazard-item">
                    <div className="hazard-header">
                      <span className="hazard-type">{h.type}</span>
                      <span
                        className="severity-tag"
                        style={{ color: SEVERITY_COLOR[h.severity] || "#64748b" }}
                      >
                        {h.severity}
                      </span>
                    </div>
                    <p className="hazard-location">📍 {h.location}</p>
                    <p className="hazard-desc">{h.description}</p>
                    <p className="hazard-rec">✅ {h.recommendation}</p>
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
