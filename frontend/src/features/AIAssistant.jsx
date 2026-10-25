import { useState, useRef, useEffect } from "react";
import { askAssistant } from "../services/api";
import ResultCard from "../components/ResultCard";
import Spinner from "../components/Spinner";

export default function AIAssistant({ backendStatus }) {
  const [question, setQuestion] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim()) { setError("Please enter a question."); return; }
    const q = question.trim();
    setLoading(true); setError(""); setQuestion("");
    try {
      const result = await askAssistant(q, context);
      setHistory((h) => [...h, { question: q, result }]);
    } catch (err) {
      setError(err.message || "Failed to get answer.");
    } finally {
      setLoading(false);
    }
  }

  function handleSuggestion(s) {
    setQuestion(s);
  }

  const SUGGESTED = [
    "What is the minimum concrete cover for reinforced concrete beams?",
    "How do I calculate the load-bearing capacity of a column?",
    "What are OSHA requirements for scaffolding height?",
    "How to estimate cement and sand for a 1000 sq ft floor?",
  ];

  return (
    <div className="feature-panel assistant-panel">
      {history.length === 0 && (
        <div className="assistant-welcome">
          <div className="assistant-avatar">🤖</div>
          <h3>AI Construction Assistant</h3>
          <p>Ask anything about construction engineering, safety, materials, codes, or project management.</p>
          <div className="suggestion-chips">
            {SUGGESTED.map((s, i) => (
              <button key={i} className="chip" onClick={() => handleSuggestion(s)}>{s}</button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-history">
        {history.map((item, i) => (
          <div key={i} className="chat-entry">
            <div className="chat-question">
              <span className="chat-bubble user-bubble">{item.question}</span>
            </div>
            <div className="chat-answer">
              <div className="assistant-icon">🤖</div>
              <div className="answer-content">
                <p className="answer-text">{item.result.answer}</p>

                {item.result.references?.length > 0 && (
                  <div className="answer-refs">
                    <span className="refs-label">📚 References:</span>
                    {item.result.references.map((r, j) => (
                      <span key={j} className="ref-tag">{r}</span>
                    ))}
                  </div>
                )}

                {item.result.follow_up_suggestions?.length > 0 && (
                  <div className="follow-ups">
                    <span className="refs-label">💡 You might also ask:</span>
                    {item.result.follow_up_suggestions.map((s, j) => (
                      <button key={j} className="chip chip-small" onClick={() => handleSuggestion(s)}>{s}</button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit} className="assistant-form">
        <div className="form-group">
          <label>Project context (optional)</label>
          <input type="text" placeholder="e.g. G+5 residential building, Mumbai, RCC structure"
            value={context} onChange={(e) => setContext(e.target.value)} />
        </div>
        <div className="assistant-input-row">
          <textarea
            className="assistant-input"
            placeholder="Ask a construction question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
            rows={3}
            disabled={loading}
          />
          <button
            className="btn-primary btn-send"
            type="submit"
            disabled={loading || !question.trim() || backendStatus !== "healthy"}
          >
            {loading ? <Spinner /> : "Ask →"}
          </button>
        </div>
        {backendStatus !== "healthy" && <p className="hint-text">Backend unavailable.</p>}
      </form>
    </div>
  );
}
