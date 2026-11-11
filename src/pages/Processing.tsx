import { Activity, Ban, CheckCircle2, Clock3, RefreshCw, XCircle } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { EmptyState, ProgressBar, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { api, json } from '@/lib/api'
import { formatDate, titleCase } from '@/lib/format'

export default function Processing() {
  const { jobs, videos, reels, refresh, notify } = useApp()
  const entityName = (kind: string, id: number) => kind === 'transcription' ? videos.find(video => video.id === id)?.original_name : kind === 'render' ? reels.find(reel => reel.id === id)?.title : `Publishing job #${id}`
  const cancel = async (id: string) => { try { await api(`/jobs/${id}/cancel`, json('POST')); await refresh(); notify('Cancellation requested', 'success') } catch (error) { notify(error instanceof Error ? error.message : 'Could not cancel job', 'error') } }
  return <div className="page"><PageHeader eyebrow="LOCAL WORKERS / ACTIVITY" title="Processing queue" description="Follow transcription and rendering progress, inspect errors, or cancel active local work." actions={<button className="button secondary" onClick={() => void refresh()}><RefreshCw size={16} />Refresh</button>} />
    <section className="queue-summary"><div><Activity /><span>Active</span><strong>{jobs.filter(job => ['running', 'queued'].includes(job.status)).length}</strong></div><div><CheckCircle2 /><span>Completed</span><strong>{jobs.filter(job => job.status === 'completed').length}</strong></div><div><XCircle /><span>Failed</span><strong>{jobs.filter(job => job.status === 'failed').length}</strong></div></section>
    <section className="panel table-panel">{jobs.length === 0 ? <EmptyState icon={<Clock3 />} title="No processing jobs yet" description="Start a transcription or render to see local worker activity here." /> : <div className="responsive-table"><table><thead><tr><th>Task</th><th>Media</th><th>Status</th><th>Progress</th><th>Updated</th><th></th></tr></thead><tbody>{jobs.map(job => <tr key={job.id}><td><strong>{titleCase(job.kind)}</strong><small className="table-sub">#{job.id.slice(0, 8)}</small></td><td>{entityName(job.kind, job.entity_id) || `Item #${job.entity_id}`}</td><td><StatusPill status={job.status} />{job.error && <small className="error-line" title={job.error}>{job.error}</small>}</td><td><div className="table-progress"><ProgressBar value={job.progress} /><span>{job.stage} · {Math.round(job.progress)}%</span></div></td><td>{formatDate(job.updated_at)}</td><td>{['running', 'queued'].includes(job.status) && <button className="icon-button" onClick={() => void cancel(job.id)} aria-label={`Cancel ${job.kind}`}><Ban size={17} /></button>}</td></tr>)}</tbody></table></div>}</section>
  </div>
}
