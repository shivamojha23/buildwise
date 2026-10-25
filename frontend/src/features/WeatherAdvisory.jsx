import { useState } from "react";
import { getWeatherAdvisory } from "../services/api";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

const RISK_COLOR = { low: "#16a34a", medium: "#d97706", high: "#dc2626", extreme: "#7c3aed" };
const RISK_BG = { low: "#f0fdf4", medium: "#fffbeb", high: "#fff1f2", extreme: "#f5f3ff" };

export default function WeatherAdvisory({ backendStatus }) {
  const [fields, setFields] = useState({
    location: "",
    activities: "",
    date_range: "next 7 days",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function set(key, val) { setFields((f) => ({ ...f, [key]: val })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!fields.location) { setError("Location is required."); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await getWeatherAdvisory(fields));
    } catch (err) {
      setError(err.message || "Failed to get advisory.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feature-panel">
      <form onSubmit={handleSubmit} className="feature-form">
        <div className="form-row">
          <div className="form-group">
            <label>Site Location *</label>
            <input type="text" placeholder="e.g. Chennai, Tamil Nadu"
              value={fields.location} onChange={(e) => set("location", e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Period</label>
            <select value={fields.date_range} onChange={(e) => set("date_range", e.target.value)}>
              <option>today</option>
              <option>next 3 days</option>
              <option>next 7 days</option>
              <option>next 2 weeks</option>
              <option>this month</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Planned Activities</label>
          <textarea placeholder="e.g. Concrete pouring, Foundation work, Roofing, Exterior painting"
            value={fields.activities} onChange={(e) => set("activities", e.target.value)} rows={3} />
        </div>
        <button className="btn-primary" type="submit"
          disabled={loading || backendStatus !== "healthy"}>
          {loading ? <><Spinner /> Generating Advisory...</> : "Get Weather Advisory"}
        </button>
        {backendStatus !== "healthy" && <p className="hint-text">Backend unavailable.</p>}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div className="risk-banner" style={{ background: RISK_BG[result.risk_level] || "#f0f6f1" }}>
            <span className="risk-badge" style={{ background: RISK_COLOR[result.risk_level] || "#64748b" }}>
              {result.risk_level?.toUpperCase()} RISK
            </span>
            <span className="ppe-badge">📍 {result.location}</span>
            <span className="ppe-badge">🌤 {result.current_conditions}</span>
          </div>

          <p className="result-summary">{result.summary}</p>

          <ResultCard title="🕐 Safe Work Window">
            <p style={{ margin: 0, fontWeight: 600, color: "#18794e" }}>{result.work_safe_window}</p>
          </ResultCard>

          {result.affected_activities?.length > 0 && (
            <ResultCard title="⚠ Activities at Risk">
              <ul className="action-list">
                {result.affected_activities.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </ResultCard>
          )}

          {result.recommendations?.length > 0 && (
            <ResultCard title="✅ Recommendations">
              <ul className="action-list">
                {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  );
}
