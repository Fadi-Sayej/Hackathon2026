import { useRef, useState } from 'react'
import { Button } from '../components/shared/Button.jsx'
import { StatusBadge } from '../components/shared/StatusBadge.jsx'
import { useT } from '../lib/i18n/index.js'
import { CONNECTOR_MODES, EXPECTED_POS_FIELDS } from '../lib/posConnectors/index.js'

export function DataSourcePage({
  storeData,
  connectorStatus,
  onSelectDemoSource,
  onSelectCsvSource,
  onSelectComaxSource,
}) {
  const t = useT()
  const fileInputRef = useRef(null)
  const [pendingFileName, setPendingFileName] = useState(null)

  const activeMode = storeData?.connectorMode ?? CONNECTOR_MODES.DEMO
  const issues = storeData?.validationIssues ?? []
  const isLoading = connectorStatus?.state === 'loading'

  async function handleFilePick(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setPendingFileName(file.name)
    const ok = await onSelectCsvSource(file)
    if (!ok && fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function openFileDialog() {
    fileInputRef.current?.click()
  }

  const sourceCards = [
    {
      mode: CONNECTOR_MODES.DEMO,
      label: t('ds.bundled'),
      description:
        'The real YomYom POS catalog exported to the app (falls back to a small demo sample if the export is absent). Always available, no upload required.',
      action: (
        <Button
          disabled={isLoading || activeMode === CONNECTOR_MODES.DEMO}
          onClick={onSelectDemoSource}
          tone="primary"
        >
          {activeMode === CONNECTOR_MODES.DEMO ? t('ds.currentlyActive') : t('ds.useDemo')}
        </Button>
      ),
      meta: (
        <StatusBadge tone={activeMode === CONNECTOR_MODES.DEMO ? 'success' : 'neutral'}>
          {activeMode === CONNECTOR_MODES.DEMO ? 'Active' : 'Available'}
        </StatusBadge>
      ),
    },
    {
      mode: CONNECTOR_MODES.CSV,
      label: t('ds.uploadCsv'),
      description:
        'Drop in a POS export. The file is parsed in the browser and fed through the same adapter pipeline as the demo data.',
      action: (
        <>
          <input
            accept=".csv,text/csv"
            aria-label={t('ds.uploadLabel')}
            onChange={handleFilePick}
            ref={fileInputRef}
            style={{ display: 'none' }}
            type="file"
          />
          <Button disabled={isLoading} onClick={openFileDialog} tone="primary">
            {activeMode === CONNECTOR_MODES.CSV ? t('ds.replaceCsv') : t('ds.chooseCsv')}
          </Button>
        </>
      ),
      meta: (
        <StatusBadge tone={activeMode === CONNECTOR_MODES.CSV ? 'success' : 'neutral'}>
          {activeMode === CONNECTOR_MODES.CSV ? 'Active' : 'Available'}
        </StatusBadge>
      ),
    },
    {
      mode: CONNECTOR_MODES.COMAX,
      label: t('ds.comax'),
      description:
        'Live Comax sync. Disabled in the frontend — a backend proxy must hold the API key and perform the outbound call.',
      action: (
        <Button disabled onClick={onSelectComaxSource} tone="ghost">
          Backend proxy required
        </Button>
      ),
      meta: <StatusBadge tone="warning">{t('ds.disabled')}</StatusBadge>,
    },
  ]

  return (
    <>
      <section className="data-source-summary panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Active source</p>
            <h2>{describeSource(storeData, t)}</h2>
            <p className="page-description">{describeStatus(connectorStatus, t)}</p>
          </div>
          <div className="data-source-summary-meta">
            <StatusBadge tone={statusTone(connectorStatus?.state)}>
              {connectorStatus?.state ?? 'idle'}
            </StatusBadge>
            <span className="metric-chip">{storeData?.products?.length ?? 0} products</span>
            <span className="metric-chip">{issues.length} validation issues</span>
          </div>
        </div>
        {connectorStatus?.hint && (
          <p className="data-source-hint">{connectorStatus.hint}</p>
        )}
      </section>

      <section className="data-source-grid">
        {sourceCards.map((card) => (
          <article
            className={`data-source-card ${activeMode === card.mode ? 'data-source-card-active' : ''}`}
            key={card.mode}
          >
            <header className="data-source-card-heading">
              <h3>{card.label}</h3>
              {card.meta}
            </header>
            <p>{card.description}</p>
            <footer className="data-source-card-footer">{card.action}</footer>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Schema reference</p>
            <h2>{t('ds.expectedFields')}</h2>
            <p className="page-description">
              Any connector (CSV, Comax, or future) should produce rows that map to these fields.
              Aliases are accepted by the data adapter.
            </p>
          </div>
        </div>
        <div className="data-source-table-wrap">
          <table className="data-source-table">
            <thead>
              <tr>
                <th>{t('ds.field')}</th>
                <th>{t('ds.aliases')}</th>
                <th>{t('ds.required')}</th>
              </tr>
            </thead>
            <tbody>
              {EXPECTED_POS_FIELDS.map((field) => (
                <tr key={field.field}>
                  <td><code>{field.field}</code></td>
                  <td>{field.aliases.length ? field.aliases.join(', ') : '—'}</td>
                  <td>
                    <StatusBadge tone={field.required ? 'danger' : 'neutral'}>
                      {field.required ? t('ds.required') : t('ds.optional')}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {issues.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Validation</p>
              <h2>Data quality warnings ({issues.length})</h2>
            </div>
          </div>
          <ul className="data-source-issues">
            {issues.slice(0, 12).map((issue, idx) => (
              <li key={`${issue.productId ?? 'row'}-${issue.code}-${idx}`}>
                <StatusBadge tone={issue.severity === 'info' ? 'info' : 'warning'}>
                  {issue.severity ?? 'warning'}
                </StatusBadge>
                <strong>{issue.field}</strong>
                <span>{issue.message}</span>
                {issue.productId && <small>SKU {issue.productId}</small>}
              </li>
            ))}
          </ul>
          {issues.length > 12 && (
            <p className="data-source-issues-note">
              Showing 12 of {issues.length} issues. Cleaner POS exports reduce this list.
            </p>
          )}
        </section>
      )}

      {pendingFileName && (
        <p className="data-source-pending">
          Last uploaded file: <strong>{pendingFileName}</strong>
        </p>
      )}
    </>
  )
}

function describeSource(storeData, t) {
  if (!storeData) return t('ds.noDataLoaded')
  if (storeData.connectorMode === CONNECTOR_MODES.CSV) {
    return `CSV upload${storeData.fileName ? ` — ${storeData.fileName}` : ''}`
  }
  if (storeData.connectorMode === CONNECTOR_MODES.COMAX) return t('ds.comaxStub')
  return t('ds.bundledDemo')
}

function describeStatus(connectorStatus, t) {
  if (!connectorStatus) return t('ds.ready')
  if (connectorStatus.state === 'loading') return connectorStatus.message ?? t('common.loading')
  if (connectorStatus.state === 'error') return connectorStatus.message ?? t('ds.loadFailed')
  return connectorStatus.message ?? t('ds.ready')
}

function statusTone(state) {
  if (state === 'error') return 'danger'
  if (state === 'loading') return 'warning'
  if (state === 'ready') return 'success'
  return 'neutral'
}
