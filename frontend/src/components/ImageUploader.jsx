import { useRef } from "react";

export default function ImageUploader({ file, onChange }) {
  const inputRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) onChange(dropped);
  }

  return (
    <div
      className={`image-uploader ${file ? "has-file" : ""}`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      aria-label="Upload image"
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: "none" }}
        onChange={(e) => onChange(e.target.files?.[0] || null)}
      />
      {file ? (
        <div className="uploader-preview">
          <img
            src={URL.createObjectURL(file)}
            alt="Preview"
            className="preview-img"
          />
          <div className="preview-info">
            <p className="preview-name">{file.name}</p>
            <p className="preview-size">{(file.size / 1024).toFixed(1)} KB</p>
            <button
              type="button"
              className="btn-remove"
              onClick={(e) => { e.stopPropagation(); onChange(null); }}
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div className="uploader-empty">
          <span className="uploader-icon">📷</span>
          <p className="uploader-text">Drop an image or click to browse</p>
          <p className="uploader-hint">JPG, PNG, WEBP — max 10 MB</p>
        </div>
      )}
    </div>
  );
}
