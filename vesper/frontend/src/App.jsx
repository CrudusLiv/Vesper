import { useState, useEffect } from 'react'
import { StoreProvider, useStore } from './state/store.jsx'
import { getSecret, setSecret as persistSecret } from './api/client.js'
import Unlock from './components/Unlock.jsx'
import Dashboard from './Dashboard.jsx'

function Gate() {
  const { state, dispatch } = useStore()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    const existing = getSecret()
    if (existing) dispatch({ type: 'UNLOCK', secret: existing })
    setChecked(true)
  }, [dispatch])

  if (!checked) return null
  if (!state.auth.unlocked) {
    return <Unlock onUnlock={(secret) => { persistSecret(secret); dispatch({ type: 'UNLOCK', secret }) }} />
  }
  return <Dashboard />
}

export default function App() {
  return (
    <StoreProvider>
      <Gate />
    </StoreProvider>
  )
}
