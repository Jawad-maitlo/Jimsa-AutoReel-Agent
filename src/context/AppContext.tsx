/* eslint-disable react-refresh/only-export-components -- Context provider and its hook intentionally share one module. */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '@/lib/api'
import type { AppSettings, PageId, ProcessingJob, Project, PublishJob, Reel, SocialAccount, SystemStatus, Video } from '@/types'
import { Toasts } from '@/components/UI'
import type { ToastMessage } from '@/components/UI'

interface AppData {
  page: PageId; navigate: (page: PageId) => void
  projects: Project[]; videos: Video[]; reels: Reel[]; jobs: ProcessingJob[]; accounts: SocialAccount[]; publishJobs: PublishJob[]
  status: SystemStatus | null; settings: AppSettings | null; loading: boolean; connected: boolean
  selectedProjectId: number | null; setSelectedProjectId: (id: number | null) => void
  selectedVideoId: number | null; setSelectedVideoId: (id: number | null) => void
  selectedReelId: number | null; setSelectedReelId: (id: number | null) => void
  refresh: () => Promise<void>; notify: (text: string, kind?: ToastMessage['kind']) => void
}

const Context = createContext<AppData | null>(null)
const pages: PageId[] = ['dashboard', 'library', 'create', 'reels', 'processing', 'publishing', 'accounts', 'settings']

export function AppProvider({ children }: { children: ReactNode }) {
  const initial = window.location.hash.slice(1) as PageId
  const [page, setPage] = useState<PageId>(pages.includes(initial) ? initial : 'dashboard')
  const [projects, setProjects] = useState<Project[]>([]); const [videos, setVideos] = useState<Video[]>([])
  const [reels, setReels] = useState<Reel[]>([]); const [jobs, setJobs] = useState<ProcessingJob[]>([])
  const [accounts, setAccounts] = useState<SocialAccount[]>([]); const [publishJobs, setPublishJobs] = useState<PublishJob[]>([])
  const [status, setStatus] = useState<SystemStatus | null>(null); const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true); const [connected, setConnected] = useState(true)
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [selectedVideoId, setSelectedVideoId] = useState<number | null>(null); const [selectedReelId, setSelectedReelId] = useState<number | null>(null)
  const [toasts, setToasts] = useState<ToastMessage[]>([]); const toastId = useRef(0)
  const activeSignature = useRef('')

  const notify = useCallback((text: string, kind: ToastMessage['kind'] = 'info') => {
    const id = ++toastId.current
    setToasts(current => [...current, { id, text, kind }])
    window.setTimeout(() => setToasts(current => current.filter(item => item.id !== id)), kind === 'error' ? 9000 : 4500)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [p, v, r, j, a, pub, sys, cfg] = await Promise.all([
        api<Project[]>('/projects'), api<Video[]>('/videos'), api<Reel[]>('/reels'), api<ProcessingJob[]>('/jobs'),
        api<SocialAccount[]>('/social/accounts'), api<PublishJob[]>('/social/publish-jobs'), api<SystemStatus>('/system/status'), api<AppSettings>('/settings'),
      ])
      setProjects(p); setVideos(v); setReels(r); setJobs(j); setAccounts(a); setPublishJobs(pub); setStatus(sys); setSettings(cfg); setConnected(true)
      setSelectedProjectId(current => current && p.some(item => item.id === current) ? current : p[0]?.id ?? null)
      setSelectedVideoId(current => current && v.some(item => item.id === current) ? current : v[0]?.id ?? null)
      setSelectedReelId(current => current && r.some(item => item.id === current) ? current : r[0]?.id ?? null)
      const signature = j.filter(job => ['queued', 'running'].includes(job.status)).map(job => `${job.id}:${job.status}`).join('|')
      if (activeSignature.current && signature !== activeSignature.current) {
        // A second pass picks up entity status and output URLs after a job finishes.
        window.setTimeout(() => void refresh(), 250)
      }
      activeSignature.current = signature
    } catch (error) {
      setConnected(false)
      if (loading) notify(error instanceof Error ? error.message : 'Local API unavailable', 'error')
    } finally { setLoading(false) }
  }, [loading, notify])

  useEffect(() => { void refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const timer = window.setInterval(() => { if (connected) void refresh() }, 3500)
    return () => window.clearInterval(timer)
  }, [connected, refresh])
  useEffect(() => {
    const listener = () => { void refresh() }
    window.addEventListener('message', listener)
    return () => window.removeEventListener('message', listener)
  }, [refresh])

  const navigate = useCallback((next: PageId) => { setPage(next); window.location.hash = next; window.scrollTo(0, 0) }, [])
  const value = useMemo(() => ({ page, navigate, projects, videos, reels, jobs, accounts, publishJobs, status, settings, loading, connected,
    selectedProjectId, setSelectedProjectId, selectedVideoId, setSelectedVideoId, selectedReelId, setSelectedReelId, refresh, notify }),
    [page, navigate, projects, videos, reels, jobs, accounts, publishJobs, status, settings, loading, connected, selectedProjectId, selectedVideoId, selectedReelId, refresh, notify])
  return <Context.Provider value={value}>{children}<Toasts messages={toasts} dismiss={id => setToasts(current => current.filter(item => item.id !== id))} /></Context.Provider>
}

export function useApp() {
  const value = useContext(Context)
  if (!value) throw new Error('useApp must be used inside AppProvider')
  return value
}
