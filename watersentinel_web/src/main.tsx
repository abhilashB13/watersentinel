import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// StrictMode removed — it causes double-mount in dev which
// breaks setInterval/setTimeout chains in AgentProgress
ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />
)
