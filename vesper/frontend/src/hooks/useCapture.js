import { useCallback } from 'react'
import { useStore } from '../state/store.jsx'
import { api, AuthError, clearSecret } from '../api/client.js'

// Write actions for the capture panels. Mirrors useVesper's 401 handling: a
// stale/bad secret drops the UI back to the unlock gate. Non-auth errors
// (including ConflictError for the schedule replace flow) propagate to the
// caller. All callbacks are stable (useCallback) so panel effects don't loop.
export function useCapture() {
  const { dispatch } = useStore()

  const lock = useCallback(() => {
    clearSecret()
    dispatch({ type: 'LOCK' })
  }, [dispatch])

  const guard = useCallback(async (fn) => {
    try {
      return await fn()
    } catch (err) {
      if (err instanceof AuthError) { lock(); return undefined }
      throw err
    }
  }, [lock])

  const logFinance = useCallback((amount, category, note) => guard(() => api.finance(amount, category, note)), [guard])
  const loadFinanceSummary = useCallback(() => guard(() => api.financeSummary()), [guard])
  const saveNote = useCallback((text) => guard(() => api.note(text)), [guard])
  const getSchedule = useCallback(() => guard(() => api.getSchedule()), [guard])
  const saveSchedule = useCallback((text, confirm) => guard(() => api.setSchedule(text, confirm)), [guard])
  const listVault = useCallback((dir) => guard(() => api.vaultList(dir)), [guard])
  const deleteVaultFile = useCallback((path) => guard(() => api.vaultDelete(path)), [guard])
  const undoVault = useCallback(() => guard(() => api.vaultUndo()), [guard])

  return { logFinance, loadFinanceSummary, saveNote, getSchedule, saveSchedule, listVault, deleteVaultFile, undoVault }
}
