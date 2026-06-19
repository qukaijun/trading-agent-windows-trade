import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/ErrorBoundary'

const root = document.getElementById('root')!
try {
  createRoot(root).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>
  )
} catch (e) {
  root.innerHTML = '<div style="padding:40px;font-family:monospace;color:red"><h2>React Error</h2><pre>' + String(e) + '</pre></div>'
}
