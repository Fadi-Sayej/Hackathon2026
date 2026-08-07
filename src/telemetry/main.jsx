import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { TelemetryDashboard } from './TelemetryDashboard.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TelemetryDashboard />
  </StrictMode>,
)
