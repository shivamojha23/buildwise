import { useState } from "react";
import { generateReport } from "../services/api";
import ImageUploader from "../components/ImageUploader";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

const PROGRESS_COLOR = {
  "behind-schedule": "#dc2626",
  "on-schedule": "#d97706",
  "ahead-of-schedule": "#16a34a",
};

export default function DailySiteReport({ backendStatus }) {
  const [fields, setFields] = useState({
    site_name: "",
    date: new Date().toISOString().split("T")[0],
    activities_completed: "",
    workers_present: "",
    equipment_used: "",
    issues: "",
    notes: "",
  });
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function set(key, val) { setFields((f) => ({ ...f, [key]: val })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!fields.site_name || !fields.date) { setError("Site name and date are required."); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await generateReport(fields, imageFile));
    } catch (err) {
      setError(err.message || "Failed to generate report.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feature-panel">
      <form onSubmit={handleSubmit} className="feature-form">
        <div className="form-row">
          <div className="form-group">
            <label>Site Name *</label>
            <input type="text" placeholder="e.g. Tower A - Andheri Project"
              value={fields.site_name} onChange={(e) => set("site_name", e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Date *</label>
            <input type="date" value={fields.date}
              onChange={(e) => set("date", e.target.value)} required />
          </div>
        </div>
        <div className="form-group">
          <label>Activities Completed</label>
          <textarea placeholder="Describe work done today..."
            value={fields.activities_completed} onChange={(e) => set("activities_completed", e.target.value)} rows={3} />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Workers Present</label>
            <input type="number" placeholder="0" value={fields.workers_present}
              onChange={(e) => set("workers_present", e.target.value)} min={0} />
          </div>
          <div className="form-group">
            <label>Equipment Used</label>
            <input type="text" placeholder="e.g. Crane, Mixer, Scaffolding"
              value={fields.equipment_used} onChange={(e) => set("equipment_used", e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label>Issues / Observations</label>
          <textarea placeholder="Any problems, delays, or safety concerns..."
            value={fields.issues} onChange={(e) => set("issues", e.target.value)} rows={2} />
        </div>
        <div className="form-group">
          <label>Additional Notes</label>
          <textarea placeholder="Any other relevant information..."
            value={fields.notes} onChange={(e) => set("notes", e.target.value)} rows={2} />
        </div>

        <div className="form-group">
          <label>Site Photo (optional)</label>
          <ImageUploader file={imageFile} onChange={(f) => { setImageFile(f); setResult(null); }} />
        </div>

        <button className="btn-primary" type="submit"
          disabled={loading || backendStatus !== "healthy"}>
          {loading ? <><Spinner /> Generating Report...</> : "Generate Daily Report"}
        </button>
        {backendStatus !== "healthy" && <p className="hint-text">Backend unavailable.</p>}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div className="risk-banner" style={{ background: "#f0fdf4" }}>
            <span className="risk-badge" style={{ background: PROGRESS_COLOR[result.overall_progress] || "#64748b" }}>
              {result.overall_progress?.replace(/-/g, " ").toUpperCase()}
            </span>
            <span className="ppe-badge">📋 {result.site_name}</span>
            <span className="ppe-badge">📅 {result.date}</span>
          </div>

          <p className="result-summary">{result.summary}</p>

          {result.sections?.map((s, i) => (
            <ResultCard key={i} title={s.section}>
              <p style={{ margin: 0, whiteSpace: "pre-line" }}>{s.content}</p>
            </ResultCard>
          ))}

          {result.issues_flagged?.length > 0 && (
            <ResultCard title="🚩 Issues Flagged">
              <ul className="action-list">
                {result.issues_flagged.map((issue, i) => <li key={i}>{issue}</li>)}
              </ul>
            </ResultCard>
          )}

          <ResultCard title="📌 Next Day Plan">
            <p style={{ margin: 0 }}>{result.next_day_plan}</p>
          </ResultCard>
        </div>
      )}
    </div>
  );
}
