import { AppProvider, useApp } from '@/context/AppContext'
import { Layout } from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Library from '@/pages/Library'
import CreateReel from '@/pages/CreateReel'
import Reels from '@/pages/Reels'
import Processing from '@/pages/Processing'
import Publishing from '@/pages/Publishing'
import Accounts from '@/pages/Accounts'
import Settings from '@/pages/Settings'
import { Spinner } from '@/components/UI'

function Workspace() {
  const { page, loading, connected, refresh } = useApp()
  if (loading) return <div className="boot-screen"><div className="brand-mark large">J</div><Spinner label="Opening local workspace" /></div>
  if (!connected) return <div className="boot-screen"><div className="offline-panel"><span className="eyebrow">LOCAL ENGINE / OFFLINE</span><h1>Start the Jimsa backend</h1><p>The interface is ready, but it cannot reach the local FastAPI service. Run <code>start_windows.bat</code> from the extracted project folder, then reopen this page.</p><button className="button primary" onClick={() => void refresh()}>Retry connection</button><code>http://127.0.0.1:8000/api/health</code></div></div>
  const pages = { dashboard: <Dashboard />, library: <Library />, create: <CreateReel />, reels: <Reels />, processing: <Processing />, publishing: <Publishing />, accounts: <Accounts />, settings: <Settings /> }
  return <Layout>{pages[page]}</Layout>
}

export default function App() {
  return <AppProvider><Workspace /></AppProvider>
}
