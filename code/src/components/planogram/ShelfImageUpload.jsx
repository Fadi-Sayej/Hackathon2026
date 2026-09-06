import { useRef, useState } from 'react'
import { Button } from '../shared/Button.jsx'

export function ShelfImageUpload({ onAnalyze, isAnalyzing }) {
  const [preview, setPreview] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef(null)

  function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target.result)
    reader.readAsDataURL(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  function handleInputChange(e) {
    handleFile(e.target.files[0])
  }

  return (
    <div className="shelf-upload">
      <div
        className={`shelf-upload-zone ${dragOver ? 'shelf-upload-zone-active' : ''} ${preview ? 'shelf-upload-zone-has-image' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !preview && fileRef.current?.click()}
      >
        {preview ? (
          <img src={preview} alt="Shelf photo preview" className="shelf-upload-preview" />
        ) : (
          <div className="shelf-upload-placeholder">
            <div className="shelf-upload-icon" aria-hidden="true">+</div>
            <p><strong>Drop a shelf photo here</strong></p>
            <p className="muted">or click to browse — JPG, PNG up to 10 MB</p>
          </div>
        )}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleInputChange}
          hidden
        />
      </div>

      <div className="shelf-upload-actions">
        {preview && (
          <>
            <Button
              tone="primary"
              onClick={() => onAnalyze()}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Shelf Compliance'}
            </Button>
            <Button
              tone="ghost"
              onClick={() => { setPreview(null); if (fileRef.current) fileRef.current.value = '' }}
            >
              Clear
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
