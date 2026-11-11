import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { CalendarClock, Check, Clapperboard, Download, Film, LoaderCircle, Play, Save, Send, Share2, Sparkles, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { EmptyState, Field, Modal, ProgressBar, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { api, json, mediaUrl } from '@/lib/api'
import { formatDuration } from '@/lib/format'
import type { PublishJob, Reel } from '@/types'

type ReelForm = Pick<Reel, 'title' | 'description' | 'hashtags' | 'subtitles_text' | 'cover_timestamp' | 'start' | 'end' | 'preset' | 'quality' | 'fit_mode' | 'burn_subtitles'>

export default function Reels() {
  const { reels, videos, jobs, accounts, selectedReelId, setSelectedReelId, navigate, refresh, notify } = useApp()
  const reel = reels.find(item => item.id === selectedReelId) || null
  const video = videos.find(item => item.id === reel?.video_id)
  const [form, setForm] = useState<ReelForm | null>(null); const [saving, setSaving] = useState(false); const [publishOpen, setPublishOpen] = useState(false)
  const [accountId, setAccountId] = useState(''); const [schedule, setSchedule] = useState(''); const [deleteOpen, setDeleteOpen] = useState(false)
  const renderJob = jobs.find(job => job.kind === 'render' && job.entity_id === reel?.id && ['running', 'queued'].includes(job.status))
  useEffect(() => { if (reel) setForm({ title: reel.title, description: reel.description, hashtags: reel.hashtags, subtitles_text: reel.subtitles_text, cover_timestamp: reel.cover_timestamp, start: reel.start, end: reel.end, preset: reel.preset, quality: reel.quality, fit_mode: reel.fit_mode, burn_subtitles: reel.burn_subtitles }) }, [reel?.id, reel?.updated_at]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (reel && accounts.length) setAccountId(String(accounts.find(account => account.platform === reel.preset)?.id ?? accounts[0].id)) }, [reel?.id, accounts]) // eslint-disable-line react-hooks/exhaustive-deps
  const set = <K extends keyof ReelForm>(key: K, value: ReelForm[K]) => setForm(current => current ? { ...current, [key]: value } : current)
  const save = async (event?: FormEvent) => {
    event?.preventDefault(); if (!reel || !form) return false; setSaving(true)
    try { await api(`/reels/${reel.id}`, json('PATCH', form)); await refresh(); notify('Reel changes saved', 'success'); return true }
    catch (error) { notify(error instanceof Error ? error.message : 'Save failed', 'error'); return false }
    finally { setSaving(false) }
  }
  const render = async () => { if (!reel || !await save()) return; try { await api(`/reels/${reel.id}/render`, json('POST')); await refresh(); notify('Rendering added to the local queue', 'success') } catch (error) { notify(error instanceof Error ? error.message : 'Render failed', 'error') } }
  const publish = async () => {
    if (!reel || !accountId) return
    try { await api<PublishJob>(`/social/reels/${reel.id}/publish`, json('POST', { account_id: Number(accountId), scheduled_at: schedule ? new Date(schedule).toISOString() : null })); setPublishOpen(false); setSchedule(''); await refresh(); notify(schedule ? 'Publishing job scheduled' : 'Publishing job queued', 'success'); navigate('publishing') }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not queue publishing', 'error') }
  }
  const remove = async () => { if (!reel) return; const id = reel.id; try { await api(`/reels/${id}`, json('DELETE')); setDeleteOpen(false); setSelectedReelId(null); await refresh(); notify('Reel and its rendered file deleted', 'success') } catch (error) { notify(error instanceof Error ? error.message : 'Delete failed', 'error') } }
  const preview = useMemo(() => reel?.output_url ? mediaUrl(reel.output_url) : video && reel ? `${mediaUrl(video.stream_url)}#t=${reel.start},${reel.end}` : '', [reel?.output_url, reel?.start, reel?.end, video]) // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="page"><PageHeader eyebrow="EDIT / REELS" title="Reel editor" description="Review the cut, refine every word, and export or publish only when you are ready." actions={reel && <><button className="button secondary" onClick={() => setDeleteOpen(true)}><Trash2 size={16} />Delete</button><button className="button primary" disabled={!reel.output_url} onClick={() => setPublishOpen(true)}><Share2 size={16} />Publish</button></>} />
    {reels.length === 0 ? <EmptyState icon={<Clapperboard />} title="No reel drafts yet" description="Choose a source video and a transcript-grounded highlight to create your first reel." action={<button className="button primary" onClick={() => navigate('create')}><Sparkles size={16} />Create a reel</button>} /> : <div className="editor-layout">
      <aside className="reel-index"><div className="section-heading"><span className="eyebrow">REEL INDEX</span><button className="icon-button" onClick={() => navigate('create')} aria-label="Create new reel"><Sparkles size={17} /></button></div>{reels.map(item => <button key={item.id} className={`reel-index-item ${item.id === reel?.id ? 'active' : ''}`} onClick={() => setSelectedReelId(item.id)}><span className="mini-reel">{item.output_url ? <video src={mediaUrl(item.output_url)} muted preload="metadata" /> : <Film />}</span><span><strong>{item.title}</strong><small>{formatDuration(item.end - item.start)} · {item.preset}</small><StatusPill status={item.status} /></span></button>)}</aside>
      {reel && form && <>
        <section className="editor-preview panel"><div className="vertical-stage"><video key={preview} src={preview} controls playsInline preload="metadata" /></div><div className="preview-caption"><div><strong>{reel.title}</strong><span>{reel.width}×{reel.height} · {reel.quality} · {reel.fit_mode}</span></div><StatusPill status={reel.status} /></div>
          {renderJob && <div className="render-progress"><div><LoaderCircle className="spin" /><strong>{renderJob.stage}</strong><span>{Math.round(renderJob.progress)}%</span></div><ProgressBar value={renderJob.progress} /></div>}
          {reel.error && <div className="error-box">{reel.error}</div>}
          <div className="preview-actions"><button className="button primary" disabled={Boolean(renderJob) || saving} onClick={() => void render()}><Play size={16} />{renderJob ? 'Rendering…' : reel.output_url ? 'Render again' : 'Render reel'}</button>{reel.output_url && <a className="button secondary" href={mediaUrl(reel.output_url)} download><Download size={16} />Download MP4</a>}</div>
        </section>
        <form className="editor-form panel" onSubmit={save}><div className="section-heading"><div><span className="eyebrow">CUT & METADATA</span><h2>Final details</h2></div><button className="button secondary small" type="submit" disabled={saving}><Save size={15} />{saving ? 'Saving' : 'Save'}</button></div>
          <Field label="Reel title"><input required maxLength={180} value={form.title} onChange={event => set('title', event.target.value)} /></Field>
          <div className="field-row three"><Field label="Start (seconds)"><input type="number" min={0} step={0.1} value={form.start} onChange={event => set('start', Number(event.target.value))} /></Field><Field label="End (seconds)"><input type="number" min={0.1} step={0.1} value={form.end} onChange={event => set('end', Number(event.target.value))} /></Field><Field label="Cover at (seconds)"><input type="number" min={0} step={0.1} value={form.cover_timestamp} onChange={event => set('cover_timestamp', Number(event.target.value))} /></Field></div>
          <div className="field-row three"><Field label="Preset"><select value={form.preset} onChange={event => set('preset', event.target.value as Reel['preset'])}><option value="youtube">YouTube Shorts</option><option value="instagram">Instagram Reels</option><option value="facebook">Facebook Reels</option></select></Field><Field label="Fit mode"><select value={form.fit_mode} onChange={event => set('fit_mode', event.target.value as Reel['fit_mode'])}><option value="crop">Crop to fill</option><option value="pad">Pad to fit</option></select></Field><Field label="Quality"><select value={form.quality} onChange={event => set('quality', event.target.value as Reel['quality'])}><option value="draft">Draft</option><option value="medium">Medium</option><option value="high">High</option></select></Field></div>
          <Field label="Description" hint="Editable before export or publishing."><textarea rows={4} value={form.description} onChange={event => set('description', event.target.value)} /></Field>
          <Field label="Hashtags"><input value={form.hashtags} onChange={event => set('hashtags', event.target.value)} placeholder="#story #creators" /></Field>
          <Field label="Captions & subtitles" hint="Standard SRT cues on the source-video timeline. Edited text and timing are burned into the next render."><textarea className="caption-editor" rows={7} value={form.subtitles_text} onChange={event => set('subtitles_text', event.target.value)} /></Field>
          <label className="toggle-label export-toggle"><input type="checkbox" checked={form.burn_subtitles} onChange={event => set('burn_subtitles', event.target.checked)} /><span>Burn the edited captions into the rendered video</span></label>
          <button className="button primary full" type="submit" disabled={saving}><Check size={16} />Save all changes</button>
        </form>
      </>}
    </div>}
    {publishOpen && reel && <Modal title={`Publish “${reel.title}”`} onClose={() => setPublishOpen(false)}>{accounts.length === 0 ? <EmptyState icon={<Share2 />} title="Connect an account first" description="Publishing requires official OAuth credentials and a connected platform account." action={<button className="button primary" onClick={() => { setPublishOpen(false); navigate('accounts') }}>Manage social accounts</button>} /> : <div className="form-stack"><Field label="Destination account"><select value={accountId} onChange={event => setAccountId(event.target.value)}>{accounts.map(account => <option key={account.id} value={account.id}>{account.platform} · {account.display_name}</option>)}</select></Field><Field label="Schedule (optional)" hint="YouTube and Facebook support scheduling here. Instagram is publish-now only."><input type="datetime-local" value={schedule} min={new Date(Date.now() + 60000).toISOString().slice(0, 16)} onChange={event => setSchedule(event.target.value)} /></Field><div className="setup-note"><CalendarClock size={16} />YouTube and Facebook receive the future publish time immediately; confirmed schedules persist in SQLite.</div><div className="modal-actions"><button className="button secondary" onClick={() => setPublishOpen(false)}>Cancel</button><button className="button primary" onClick={() => void publish()}><Send size={16} />{schedule ? 'Schedule post' : 'Queue publish now'}</button></div></div>}</Modal>}
    {deleteOpen && reel && <Modal title="Delete this reel?" onClose={() => setDeleteOpen(false)}><p className="modal-copy">The reel record and rendered MP4 will be deleted. The original source video is not changed.</p><div className="modal-actions"><button className="button secondary" onClick={() => setDeleteOpen(false)}>Cancel</button><button className="button danger" onClick={() => void remove()}>Delete reel</button></div></Modal>}
  </div>
}
