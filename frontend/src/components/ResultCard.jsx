export default function ResultCard({ title, children }) {
  return (
    <div className="result-card">
      <h4 className="result-card-title">{title}</h4>
      <div className="result-card-body">{children}</div>
    </div>
  );
}
