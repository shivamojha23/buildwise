import { useState } from "react";
import { generatePlan } from "../services/api";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

export default function ProjectPlanner({ backendStatus }) {
  const [fields, setFields] = useState({
    project_type: "",
    area_sqft: "",
    location: "",
    budget_usd: "",
    description: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function set(key, val) { setFields((f) => ({ ...f, [key]: val })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!fields.project_type || !fields.area_sqft) {
      setError("Project type and area are required.");
      return;
    }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await generatePlan(fields));
    } catch (err) {
      setError(err.message || "Failed to generate plan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feature-panel">
      <form onSubmit={handleSubmit} className="feature-form">
        <div className="form-row">
          <div className="form-group">
            <label>Project Type *</label>
            <input
              type="text"
              placeholder="e.g. Residential House, Commercial Building"
              value={fields.project_type}
              onChange={(e) => set("project_type", e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Area (sq ft) *</label>
            <input
              type="number"
              placeholder="e.g. 2500"
              value={fields.area_sqft}
              onChange={(e) => set("area_sqft", e.target.value)}
              required
              min={1}
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Location</label>
            <input
              type="text"
              placeholder="e.g. Mumbai, India"
              value={fields.location}
              onChange={(e) => set("location", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Budget (USD)</label>
            <input
              type="number"
              placeholder="e.g. 250000"
              value={fields.budget_usd}
              onChange={(e) => set("budget_usd", e.target.value)}
              min={0}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Project Description</label>
          <textarea
            placeholder="Describe the project scope, special requirements, etc."
            value={fields.description}
            onChange={(e) => set("description", e.target.value)}
            rows={3}
          />
        </div>
        <button className="btn-primary" type="submit"
          disabled={loading || backendStatus !== "healthy"}>
          {loading ? <><Spinner /> Generating Plan...</> : "Generate Project Plan"}
        </button>
        {backendStatus !== "healthy" && <p className="hint-text">Backend unavailable.</p>}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div className="risk-banner" style={{ background: "#f0fdf4" }}>
            <span className="risk-badge" style={{ background: "#18794e" }}>
              {result.project_type}
            </span>
            <span className="ppe-badge">⏱ {result.estimated_duration_weeks} weeks</span>
            <span className="ppe-badge">💰 ${result.total_estimated_cost_usd?.toLocaleString()}</span>
          </div>

          <p className="result-summary">{result.summary}</p>

          {result.phases?.length > 0 && (
            <ResultCard title="📅 Project Phases">
              <div className="phase-list">
                {result.phases.map((p, i) => (
                  <div key={i} className="phase-item">
                    <div className="phase-header">
                      <span className="phase-name">{p.phase}</span>
                      <span className="phase-duration">{p.duration_weeks} weeks</span>
                    </div>
                    {p.activities?.length > 0 && (
                      <ul className="activity-list">
                        {p.activities.map((a, j) => <li key={j}>{a}</li>)}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </ResultCard>
          )}

          {result.materials?.length > 0 && (
            <ResultCard title="🧱 Material Estimates">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr><th>Material</th><th>Quantity</th><th>Unit</th><th>Est. Cost (USD)</th></tr>
                  </thead>
                  <tbody>
                    {result.materials.map((m, i) => (
                      <tr key={i}>
                        <td>{m.material}</td>
                        <td>{m.quantity}</td>
                        <td>{m.unit}</td>
                        <td>${m.estimated_cost_usd?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ResultCard>
          )}

          {result.key_risks?.length > 0 && (
            <ResultCard title="⚠ Key Risks">
              <ul className="action-list">
                {result.key_risks.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  );
}
