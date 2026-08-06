import { useState } from 'react'
import { Button } from '../shared/Button.jsx'
import { dirProps } from '../../lib/utils/rtl.js'

export function ReportViewer({ markdown, onClose }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(markdown).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function handlePrint() {
    window.print()
  }

  const html = markdownToHtml(markdown)

  return (
    <div className="report-overlay">
      <div className="report-modal">
        <header className="report-modal-header">
          <div>
            <p className="eyebrow">AI-Generated</p>
            <h2>Shelf Optimization Report</h2>
          </div>
          <div className="report-modal-actions">
            <Button tone="ghost" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy Markdown'}
            </Button>
            <Button tone="ghost" onClick={handlePrint}>
              Print / PDF
            </Button>
            <Button tone="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </header>
        <div
          className="report-body"
          dangerouslySetInnerHTML={{ __html: html }}
          {...dirProps(markdown)}
        />
      </div>
    </div>
  )
}

function markdownToHtml(md) {
  let html = md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')

  const lines = html.split('\n')
  const result = []
  let inTable = false

  for (const line of lines) {
    if (line.startsWith('|')) {
      if (line.replace(/[|\-\s]/g, '').length === 0) continue
      const cells = line.split('|').filter(Boolean).map((c) => c.trim())
      if (!inTable) {
        result.push('<table class="report-table"><thead><tr>')
        result.push(cells.map((c) => `<th>${c}</th>`).join(''))
        result.push('</tr></thead><tbody>')
        inTable = true
      } else {
        result.push('<tr>')
        result.push(cells.map((c) => `<td>${c}</td>`).join(''))
        result.push('</tr>')
      }
    } else {
      if (inTable) {
        result.push('</tbody></table>')
        inTable = false
      }
      if (line.startsWith('<h') || line.startsWith('<hr') || line.startsWith('<li') || line.startsWith('<table')) {
        result.push(line)
      } else if (line.trim().length > 0) {
        result.push(`<p>${line}</p>`)
      }
    }
  }
  if (inTable) result.push('</tbody></table>')

  return result.join('\n')
}
