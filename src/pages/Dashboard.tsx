import { ArrowRight, CheckCircle2, Clapperboard, Clock3, Film, FolderOpen, Plus, Sparkles } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { EmptyState, ProgressBar, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { mediaUrl } from '@/lib/api'
import { formatDuration, formatDate } from '@/lib/format'

export default function Dashboard() {
  const { projects, videos, reels, jobs, publishJobs, navigate, setSelectedVideoId, setSelectedReelId, status } = useApp()
  const active = jobs.filter(job => ['queued', 'running'].includes(job.status))
  const exported = reels.filter(reel => reel.status === 'exported').length
  const published = publishJobs.filter(job => job.status === 'published').length
  return <div className="page">
    <PageHeader eyebrow="WORKSPACE / OVERVIEW" title="Make the long story short." description="Import, find the moments worth sharing, and export vertical reels — all on your machine."
      actions={<button className="button primary" onClick={() => navigate('library')}><Plus size={17} />Import video</button>} />
    <section className="metric-grid">
      <div className="metric"><span>SOURCE VIDEOS</span><strong>{videos.length}</strong><small>{projects.length} local project{projects.length === 1 ? '' : 's'}</small><Film /></div>
      <div className="metric"><span>REELS CREATED</span><strong>{reels.length}</strong><small>{exported} exported and ready</small><Clapperboard /></div>
      <div className="metric"><span>IN PRODUCTION</span><strong>{active.length}</strong><small>{active.length ? 'Local workers active' : 'Queue is clear'}</small><Clock3 /></div>
      <div className="metric"><span>PUBLISHED</span><strong>{published}</strong><small>{publishJobs.filter(job => job.status === 'failed').length} need attention</small><CheckCircle2 /></div>
    </section>
    <div className="dashboard-grid">
      <section className="panel recent-media">
        <div className="section-heading"><div><span className="eyebrow">MEDIA INDEX</span><h2>Recent source videos</h2></div><button className="text-button" onClick={() => navigate('library')}>Open library<ArrowRight size={15} /></button></div>
        {videos.length === 0 ? <EmptyState icon={<FolderOpen />} title="Your library is ready" description="Import a long-form MP4, MOV, MKV, or WebM to begin." action={<button className="button secondary" onClick={() => navigate('library')}>Choose a video</button>} /> :
          <div className="media-list">{videos.slice(0, 4).map(video => <button className="media-row" key={video.id} onClick={() => { setSelectedVideoId(video.id); navigate('create') }}>
            <span className="media-thumb">{video.thumbnail_url ? <img src={mediaUrl(video.thumbnail_url)} alt="" /> : <Film />}<b>{formatDuration(video.duration)}</b></span>
            <span className="media-copy"><strong>{video.original_name}</strong><small>{video.width}×{video.height} · {video.has_audio ? video.audio_codec : 'No audio'}</small></span>
            <StatusPill status={video.status} /><ArrowRight size={16} />
          </button>)}</div>}
      </section>
      <aside className="dashboard-side">
        <section className="panel engine-panel"><span className="eyebrow">LOCAL ENGINE</span><h2>System at a glance</h2>
          <div className="engine-row"><span>FFmpeg</span><b className={status?.ffmpeg ? 'good' : 'bad'}>{status?.ffmpeg ? 'Ready' : 'Not found'}</b></div>
          <div className="engine-row"><span>Ollama</span><b className={status?.ollama.available ? 'good' : 'muted'}>{status?.ollama.available ? 'Connected' : 'Fallback active'}</b></div>
          <div className="engine-row"><span>Free storage</span><b>{status?.storage.free_gb ?? '—'} GB</b></div>
          <button className="button secondary full" onClick={() => navigate('settings')}>View system status</button>
        </section>
        <section className="panel activity-panel"><span className="eyebrow">ACTIVITY</span><h2>Processing now</h2>
          {active.length === 0 ? <p className="quiet">No active jobs. Your exports and transcripts will appear here.</p> : active.slice(0, 3).map(job => <div className="activity-job" key={job.id}><div><strong>{job.stage}</strong><span>{job.kind} · {Math.round(job.progress)}%</span></div><ProgressBar value={job.progress} /></div>)}
        </section>
      </aside>
    </div>
    {reels.length > 0 && <section className="panel reel-strip"><div className="section-heading"><div><span className="eyebrow">OUTPUT</span><h2>Latest reels</h2></div><button className="text-button" onClick={() => navigate('reels')}>Open editor<ArrowRight size={15} /></button></div>
      <div className="reel-cards">{reels.slice(0, 4).map(reel => <button key={reel.id} className="reel-card" onClick={() => { setSelectedReelId(reel.id); navigate('reels') }}>
        <span className="reel-visual">{reel.output_url ? <video src={mediaUrl(reel.output_url)} muted preload="metadata" /> : <Clapperboard />}<b>{reel.preset}</b></span><strong>{reel.title}</strong><small>{formatDate(reel.created_at)}</small><StatusPill status={reel.status} />
      </button>)}</div></section>}
    <button className="floating-create" onClick={() => navigate('create')} aria-label="Create a reel"><Sparkles size={20} /><span>Create reel</span></button>
  </div>
}
