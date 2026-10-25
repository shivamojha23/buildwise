import { useState } from "react";
import { estimateValuation } from "../services/api";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

const TREND_COLOR = { declining: "#dc2626", stable: "#d97706", appreciating: "#16a34a", hot: "#7c3aed" };

export default function PropertyValuation({ backendStatus }) {
  const [fields, setFields] = useState({
    property_type: "",
    area_sqft: "",
    location: "",
    bedrooms: "",
    bathrooms: "",
    year_built: "",
    condition: "good",
    amenities: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function set(key, val) { setFields((f) => ({ ...f, [key]: val })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!fields.property_type || !fields.area_sqft || !fields.location) {
      setError("Property type, area, and location are required.");
      return;
    }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await estimateValuation(fields));
    } catch (err) {
      setError(err.message || "Valuation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="feature-panel">
      <form onSubmit={handleSubmit} className="feature-form">
        <div className="form-row">
          <div className="form-group">
            <label>Property Type *</label>
            <input type="text" placeholder="e.g. Residential, Commercial, Industrial"
              value={fields.property_type} onChange={(e) => set("property_type", e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Location *</label>
            <input type="text" placeholder="e.g. Mumbai, Maharashtra"
              value={fields.location} onChange={(e) => set("location", e.target.value)} required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Area (sq ft) *</label>
            <input type="number" placeholder="e.g. 1200" value={fields.area_sqft}
              onChange={(e) => set("area_sqft", e.target.value)} required min={1} />
          </div>
          <div className="form-group">
            <label>Condition</label>
            <select value={fields.condition} onChange={(e) => set("condition", e.target.value)}>
              <option value="poor">Poor</option>
              <option value="fair">Fair</option>
              <option value="good">Good</option>
              <option value="excellent">Excellent</option>
              <option value="new">New Construction</option>
            </select>
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Bedrooms</label>
            <input type="number" placeholder="0" value={fields.bedrooms}
              onChange={(e) => set("bedrooms", e.target.value)} min={0} />
          </div>
          <div className="form-group">
            <label>Bathrooms</label>
            <input type="number" placeholder="0" value={fields.bathrooms}
              onChange={(e) => set("bathrooms", e.target.value)} min={0} />
          </div>
          <div className="form-group">
            <label>Year Built</label>
            <input type="number" placeholder="e.g. 2010" value={fields.year_built}
              onChange={(e) => set("year_built", e.target.value)} min={1800} max={2030} />
          </div>
        </div>
        <div className="form-group">
          <label>Amenities</label>
          <input type="text" placeholder="e.g. Parking, Pool, Gym, Garden, Solar panels"
            value={fields.amenities} onChange={(e) => set("amenities", e.target.value)} />
        </div>
        <button className="btn-primary" type="submit"
          disabled={loading || backendStatus !== "healthy"}>
          {loading ? <><Spinner /> Estimating...</> : "Estimate Valuation"}
        </button>
        {backendStatus !== "healthy" && <p className="hint-text">Backend unavailable.</p>}
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="results">
          <div className="valuation-hero">
            <div className="valuation-main">
              <p className="valuation-label">Estimated Value</p>
              <h2 className="valuation-value">${result.estimated_value_usd?.toLocaleString()}</h2>
              <p className="valuation-psf">${result.price_per_sqft_usd?.toLocaleString()} / sq ft</p>
            </div>
            <div className="valuation-meta">
              <div className="meta-item">
                <span className="meta-label">Market Trend</span>
                <span className="meta-val" style={{ color: TREND_COLOR[result.market_trend] || "#374151" }}>
                  {result.market_trend}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Confidence</span>
                <span className="meta-val">{result.confidence_level}</span>
              </div>
            </div>
          </div>

          <p className="result-summary">{result.summary}</p>

          {result.comparable_range_usd && (
            <ResultCard title="📊 Comparable Range">
              <div className="range-row">
                <div className="range-item">
                  <span className="range-label">Low</span>
                  <span className="range-val">${result.comparable_range_usd.low?.toLocaleString()}</span>
                </div>
                <div className="range-item range-mid">
                  <span className="range-label">Mid</span>
                  <span className="range-val">${result.comparable_range_usd.mid?.toLocaleString()}</span>
                </div>
                <div className="range-item">
                  <span className="range-label">High</span>
                  <span className="range-val">${result.comparable_range_usd.high?.toLocaleString()}</span>
                </div>
              </div>
            </ResultCard>
          )}

          {result.value_drivers?.length > 0 && (
            <ResultCard title="📈 Value Drivers">
              <ul className="action-list">
                {result.value_drivers.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </ResultCard>
          )}
        </div>
      )}
    </div>
  );
}
