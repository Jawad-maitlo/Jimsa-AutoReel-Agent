import { Clapperboard, Film, FolderOpen, LayoutDashboard, ListVideo, Menu, Radio, Settings, Share2, Sparkles, X, Zap } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { useApp } from '@/context/AppContext'
import type { PageId } from '@/types'

const nav: { id: PageId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard }, { id: 'library', label: 'Video library', icon: FolderOpen },
  { id: 'create', label: 'Create reel', icon: Sparkles }, { id: 'reels', label: 'Reel editor', icon: Clapperboard },
  { id: 'processing', label: 'Processing', icon: Zap }, { id: 'publishing', label: 'Publishing', icon: Share2 },
  { id: 'accounts', label: 'Social accounts', icon: Radio }, { id: 'settings', label: 'Settings', icon: Settings },
]

export function Layout({ children }: { children: ReactNode }) {
  const { page, navigate, jobs, connected } = useApp(); const [open, setOpen] = useState(false)
  const active = jobs.filter(job => ['queued', 'running'].includes(job.status)).length
  const go = (id: PageId) => { navigate(id); setOpen(false) }
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><span className="brand-mark"><Film size={22} strokeWidth={1.7} /></span><div><strong>JIMSA</strong><span>AUTOREEL AGENT</span></div><button className="mobile-close" onClick={() => setOpen(false)} aria-label="Close navigation"><X /></button></div>
      <nav className="main-nav" aria-label="Main navigation">{nav.map(item => { const Icon = item.icon; return <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => go(item.id)}>
        <Icon size={18} strokeWidth={1.7} /><span>{item.label}</span>{item.id === 'processing' && active > 0 && <b>{active}</b>}
      </button> })}</nav>
      <div className="sidebar-foot"><div className={`connection ${connected ? 'online' : 'offline'}`}><span />{connected ? 'Local engine online' : 'Local engine offline'}</div><p>LOCAL-FIRST · v1.0</p></div>
    </aside>
    {open && <button className="nav-scrim" onClick={() => setOpen(false)} aria-label="Close navigation overlay" />}
    <main className="main-area"><header className="mobile-header"><button onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></button><strong>JIMSA / AUTOREEL</strong><ListVideo size={20} /></header>{children}</main>
  </div>
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</header>
}
