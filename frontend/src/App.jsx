import { useEffect, useState } from "react";
import { checkBackendHealth, getFeatures } from "./services/api";

import SafetyMonitoring from "./features/SafetyMonitoring";
import CrackDetection from "./features/CrackDetection";
import ProjectPlanner from "./features/ProjectPlanner";
import PropertyValuation from "./features/PropertyValuation";
import WeatherAdvisory from "./features/WeatherAdvisory";
import DailySiteReport from "./features/DailySiteReport";
import AIAssistant from "./features/AIAssistant";

import "./App.css";

// Map feature id → component
const FEATURE_COMPONENTS = {
  safety: SafetyMonitoring,
  cracks: CrackDetection,
  planning: ProjectPlanner,
  valuation: PropertyValuation,
  weather: WeatherAdvisory,
  reports: DailySiteReport,
  assistant: AIAssistant,
};

const ICONS = {
  safety: "🦺",
  cracks: "🏗️",
  planning: "📋",
  valuation: "🏢",
  weather: "🌤️",
  reports: "📝",
  assistant: "🤖",
};

const DESCRIPTIONS = {
  safety: "AI-powered hazard detection and PPE compliance analysis from site photographs.",
  cracks: "Detect, classify, and assess structural cracks with severity and remediation guidance.",
  planning: "Generate AI-assisted timelines, material estimates, and cost breakdowns.",
  valuation: "Estimate property value using location, size, condition, and market data.",
  weather: "Weather-aware scheduling and site-risk advisories for planned construction activities.",
  reports: "Auto-generate structured daily site progress reports from inputs and photos.",
  assistant: "Ask anything about construction engineering, codes, materials, or project management.",
};

export default function App() {
  const [activeFeatureId, setActiveFeatureId] = useState(null);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [aiReady, setAiReady] = useState(false);
  const [features, setFeatures] = useState([]);
  const [apiError, setApiError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const [health, featureData] = await Promise.all([
          checkBackendHealth(),
          getFeatures(),
        ]);
        setBackendStatus(health.status);
        setAiReady(health.ai_ready ?? false);
        setFeatures(
          featureData.features.map((f) => ({
            ...f,
            icon: ICONS[f.id] ?? "🔧",
            description: DESCRIPTIONS[f.id] ?? "",
          }))
        );
        setApiError("");
      } catch (err) {
        setBackendStatus("unavailable");
        setApiError(err.message);
      }
    }
    loadData();
  }, []);

  const activeFeature = features.find((f) => f.id === activeFeatureId);
  const FeatureComponent = activeFeatureId ? FEATURE_COMPONENTS[activeFeatureId] : null;

  function openFeature(id) {
    setActiveFeatureId(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">B</div>
          <div>
            <h2>BuildWise <span>AI</span></h2>
            <p>Construction intelligence</p>
          </div>
        </div>

        <p className="nav-heading">WORKSPACE</p>

        <button
          className={`nav-item ${!activeFeatureId ? "active" : ""}`}
          onClick={() => setActiveFeatureId(null)}
        >
          <span>▦</span> Overview
        </button>

        {features.map((f) => (
          <button
            key={f.id}
            className={`nav-item ${activeFeatureId === f.id ? "active" : ""}`}
            onClick={() => openFeature(f.id)}
          >
            <span>{f.icon}</span> {f.name}
          </button>
        ))}

        <div className="sidebar-footer">
          <div
            className="status-dot"
            style={{ background: backendStatus === "healthy" ? "#16a34a" : "#e5a23b" }}
          />
          <span>
            Backend: {backendStatus}
            {backendStatus === "healthy" && (
              <span style={{ marginLeft: 6 }}>
                · AI: {aiReady ? "✓" : "⚠ no key"}
              </span>
            )}
          </span>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="breadcrumb">
              Workspace / {activeFeature?.name || "Overview"}
            </p>
            <h3>BuildWise AI Platform</h3>
          </div>
          <div className="profile">BW</div>
        </header>

        {/* Hero — shown on all pages */}
        {!activeFeatureId && (
          <section className="welcome">
            <p className="eyebrow">AI-POWERED CONSTRUCTION INTELLIGENCE</p>
            <h1>Build smarter.<br /><span>Build safer.</span></h1>
            <p className="welcome-description">
              Your intelligent workspace for construction planning, site monitoring, and project insights.
            </p>
          </section>
        )}

        {/* Backend connection error */}
        {apiError && (
          <div className="alert alert-warning" style={{ marginTop: 20 }}>
            ⚠ Backend connection error: {apiError}. Make sure the FastAPI server is running.
          </div>
        )}

        {/* AI key warning */}
        {backendStatus === "healthy" && !aiReady && (
          <div className="alert alert-warning" style={{ marginTop: 20 }}>
            ⚠ AI features are disabled — set <code>OPENAI_API_KEY</code> in <code>backend/.env</code> and restart the server.
          </div>
        )}

        {/* Feature detail view */}
        {activeFeatureId && FeatureComponent ? (
          <section className="feature-detail">
            <button className="back-button" onClick={() => setActiveFeatureId(null)}>
              ← Back to overview
            </button>
            <div className="feature-detail-header">
              <span className="feature-detail-icon">{activeFeature?.icon}</span>
              <div>
                <h2>{activeFeature?.name}</h2>
                <p className="feature-detail-desc">{activeFeature?.description}</p>
              </div>
            </div>
            <FeatureComponent backendStatus={backendStatus} aiReady={aiReady} />
          </section>
        ) : (
          <>
            {/* Stats row */}
            <section className="stats">
              <article className="stat-card">
                <p>Active projects</p>
                <h2>03</h2>
                <span>Sample dashboard data</span>
              </article>
              <article className="stat-card">
                <p>AI tools</p>
                <h2>{String(features.length).padStart(2, "0")}</h2>
                <span>Available platform features</span>
              </article>
              <article className="stat-card">
                <p>AI status</p>
                <h2 style={{ color: aiReady ? "#16a34a" : "#d97706", fontSize: 18 }}>
                  {backendStatus === "healthy"
                    ? (aiReady ? "Ready" : "No key")
                    : "Offline"}
                </h2>
                <span>
                  {aiReady
                    ? "All features active"
                    : "Add OPENAI_API_KEY to enable"}
                </span>
              </article>
            </section>

            {/* Feature grid */}
            <section className="features-section">
              <div className="section-heading">
                <div>
                  <h2>Explore your workspace</h2>
                  <p>Select a feature to get started.</p>
                </div>
              </div>
              <div className="feature-grid">
                {features.map((f) => (
                  <button
                    key={f.id}
                    className="feature-card"
                    onClick={() => openFeature(f.id)}
                  >
                    <div className="feature-icon">{f.icon}</div>
                    <h3>{f.name}</h3>
                    <p>{f.description}</p>
                    <span className="card-link">Explore feature →</span>
                  </button>
                ))}
              </div>
            </section>
          </>
        )}

        <footer>
          BuildWise AI · v2.0 · Powered by GPT-4o · For demonstration purposes only.
        </footer>
      </main>
    </div>
  );
}
