import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { I18nProvider } from './lib/i18n/I18nProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* Wraps everything: the provider sets `lang` and `dir` on <html>, so the
        whole document flips rather than individual components pretending to. */}
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
)
