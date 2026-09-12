import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { I18nProvider } from './lib/i18n/I18nProvider.jsx'
import { SmoothScrollProvider } from './lib/motion/SmoothScrollProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* Wraps everything: the provider sets `lang` and `dir` on <html>, so the
        whole document flips rather than individual components pretending to. */}
    <I18nProvider>
      {/* Inside I18n, because a direction flip resets scroll and Lenis should
          re-read the document after that, not before. */}
      <SmoothScrollProvider>
        <App />
      </SmoothScrollProvider>
    </I18nProvider>
  </StrictMode>,
)
