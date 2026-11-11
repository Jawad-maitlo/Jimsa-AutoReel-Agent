import { useEffect, useRef, useState } from 'react'
import { Bot, Captions, ChevronRight, Clapperboard, FileText, Film, LoaderCircle, Play, Scissors, Sparkles, WandSparkles } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { EmptyState, Field, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { api, json, mediaUrl } from '@/lib/api'
import { clamp, formatDuration } from '@/lib/format'
import type { Highlight, Reel, Transcript } from '@/types'

export default function CreateReel() {
  const { videos, jobs, selectedVideoId, setSelectedVideoId, setSelectedReelId, navigate, refresh, notify, status } = useApp()
  const video = videos.find(item => item.id === selectedVideoId) || null
  const [transcript, setTranscript] = useState<Transcript | null>(null); const [highlights, setHighlights] = useState<Highlight[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null); const [busy, setBusy] = useState<'transcribe' | 'analyze' | 'create' | null>(null)
  const [preferLlm, setPreferLlm] = useState(true); const [count, setCount] = useState(6)
  const [preset, setPreset] = useState<'youtube' | 'instagram' | 'facebook'>('youtube'); const [fitMode, setFitMode] = useState<'crop' | 'pad'>('crop')
  const [quality, setQuality] = useState<'draft' | 'medium' | 'high'>('medium'); const [burnSubtitles, setBurnSubtitles] = useState(true)
  const player = useRef<HTMLVideoElement>(null)
  const selected = highlights.find(item => item.id === selectedId) || null
  const transcribeJob = jobs.find(job => job.kind === 'transcription' && job.entity_id === video?.id && ['running', 'queued'].includes(job.status))

  useEffect(() => {
    setTranscript(null); setHighlights([]); setSelectedId(null)
    if (!video) return
    void api<Transcript>(`/videos/${video.id}/transcript`).then(setTranscript).catch(() => setTranscript(null))
    void api<Highlight[]>(`/videos/${video.id}/highlights`).then(items => { setHighlights(items); setSelectedId(items[0]?.id ?? null) }).catch(() => setHighlights([]))
  }, [video?.id, video?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const transcribe = async () => {
    if (!video) return; setBusy('transcribe')
    try { const result = await api<{ job_id?: string; message?: string }>(`/videos/${video.id}/transcribe`, json('POST')); await refresh(); notify(result.message || 'Transcription started. You can follow its progress here.', 'success') }
    catch (error) { notify(error instanceof Error ? error.message : 'Transcription failed', 'error') }
    finally { setBusy(null) }
  }
  const analyze = async () => {
    if (!video) return; setBusy('analyze')
    try { const result = await api<Highlight[]>(`/videos/${video.id}/highlights?prefer_llm=${preferLlm}&count=${count}`, json('POST')); setHighlights(result); setSelectedId(result[0]?.id ?? null); await refresh(); notify(result[0]?.analysis_method === 'ollama' ? 'Ollama highlights ready' : 'Deterministic transcript highlights ready. No AI content was fabricated.', 'success') }
    catch (error) { notify(error instanceof Error ? error.message : 'Highlight analysis failed', 'error') }
    finally { setBusy(null) }
  }
  const selectHighlight = (item: Highlight) => { setSelectedId(item.id); if (player.current) { player.current.currentTime = item.start; void player.current.play().catch(() => undefined) } }
  const updateHighlight = async (item: Highlight, patch: Partial<Highlight>) => {
    const next = { ...item, ...patch }
    setHighlights(current => current.map(value => value.id === item.id ? next : value))
    try { await api(`/videos/highlights/${item.id}`, json('PATCH', { start: next.start, end: next.end, title: next.title, selected: next.selected })) }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not save highlight', 'error'); setHighlights(current => current.map(value => value.id === item.id ? item : value)) }
  }
  const selectedHighlights = highlights.filter(item => item.selected)
  const create = async (render: boolean) => {
    if (!video || selectedHighlights.length === 0) return; setBusy('create')
    try {
      const reels = await api<Reel[]>(`/reels/batch-from-video/${video.id}`, json('POST', {
        preset, width: 1080, height: 1920, quality, fit_mode: fitMode,
        burn_subtitles: burnSubtitles && Boolean(transcript), render,
      }))
      if (render) notify(`${reels.length} reel(s) created and queued for rendering.`, 'success')
      else notify(`${reels.length} reel draft(s) saved`, 'success')
      await refresh(); navigate('reels')
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not create reels', 'error') }
    finally { setBusy(null) }
  }

  return <div className="page create-page"><PageHeader eyebrow="CREATE / NEW REEL" title="Find the moment. Frame the story." description="Transcribe a source, select a grounded highlight, then shape a platform-ready vertical cut." />
    <div className="workflow-steps"><span className="active"><b>1</b>Source</span><ChevronRight /><span className={transcript ? 'active' : ''}><b>2</b>Transcript</span><ChevronRight /><span className={selectedHighlights.length > 0 ? 'active' : ''}><b>3</b>Highlights</span><ChevronRight /><span><b>4</b>Export</span></div>
    <div className="creator-layout">
      <section className="creator-main">
        <div className="panel source-selector"><div className="section-heading"><div><span className="eyebrow">01 / SOURCE</span><h2>Choose a recording</h2></div>{video && <StatusPill status={video.status} />}</div>
          <select value={selectedVideoId ?? ''} onChange={event => setSelectedVideoId(Number(event.target.value))} aria-label="Source video"><option value="" disabled>Select a source video</option>{videos.map(item => <option key={item.id} value={item.id}>{item.original_name} · {formatDuration(item.duration)}</option>)}</select>
          {!video ? <EmptyState icon={<Film />} title="Select a source video" description="Your imported library is available above. New videos can be added from the library." action={<button className="button secondary" onClick={() => navigate('library')}>Open video library</button>} /> :
            <div className="source-workspace"><video ref={player} src={mediaUrl(video.stream_url)} controls playsInline preload="metadata" /><div className="source-details"><span>{video.width}×{video.height}</span><span>{formatDuration(video.duration)}</span><span>{video.has_audio ? 'Audio available' : 'No audio'}</span></div></div>}
        </div>
        {video && <div className="panel transcript-panel"><div className="section-heading"><div><span className="eyebrow">02 / TRANSCRIPT</span><h2>Speech, with timestamps</h2></div>{transcript && <span className="model-label">{transcript.model} · {transcript.language}</span>}</div>
          {transcribeJob ? <div className="inline-progress"><LoaderCircle className="spin" /><div><strong>{transcribeJob.stage}</strong><span>{Math.round(transcribeJob.progress)}% · model downloads happen only on first use</span></div></div> : transcript ? <div className="transcript-scroll">{transcript.segments.slice(0, 30).map(segment => <p key={segment.id}><time>{formatDuration(segment.start)}</time><span>{segment.text}</span></p>)}{transcript.segments.length > 30 && <small>Showing first 30 of {transcript.segments.length} segments</small>}</div> : <div className="action-empty"><FileText /><div><strong>No transcript yet</strong><p>Use faster-whisper to create timestamped segments. Existing transcripts are reused automatically.</p></div><button className="button primary" disabled={busy === 'transcribe' || !video.has_audio} onClick={() => void transcribe()}>{busy === 'transcribe' ? 'Starting…' : 'Transcribe audio'}</button></div>}
          {transcript && <div className="analysis-bar"><label className="toggle-label"><input type="checkbox" checked={preferLlm} onChange={event => setPreferLlm(event.target.checked)} /><span>Use Ollama when available</span></label><select value={count} onChange={event => setCount(Number(event.target.value))} aria-label="Number of highlights">{[3, 5, 6, 7, 10].map(value => <option key={value} value={value}>{value} highlights</option>)}</select><button className="button primary" disabled={busy === 'analyze'} onClick={() => void analyze()}><WandSparkles size={16} />{busy === 'analyze' ? 'Analyzing…' : highlights.length ? 'Regenerate highlights' : 'Find highlights'}</button></div>}
          {preferLlm && transcript && <p className="setup-note"><Bot size={15} />{status?.ollama.available ? `Ollama connected. Configured model: ${status.ollama.message}` : 'Ollama is offline; analysis will clearly use the deterministic transcript fallback.'}</p>}
        </div>}
      </section>
      <aside className="creator-side">
        <div className="panel highlights-panel"><div className="section-heading"><div><span className="eyebrow">03 / HIGHLIGHTS</span><h2>Select moments ({selectedHighlights.length} of {highlights.length})</h2></div></div>
          {highlights.length === 0 ? <div className="side-empty"><Sparkles /><p>Grounded highlight candidates will appear after transcript analysis.</p></div> : <div className="highlight-list">{highlights.map(item => <article key={item.id} className={`highlight-item ${selectedId === item.id ? 'selected' : ''} ${!item.selected ? 'deselected' : ''}`}>
            <div className="highlight-header"><label className="toggle-label highlight-toggle" onClick={event => event.stopPropagation()}><input type="checkbox" checked={item.selected} onChange={() => void updateHighlight(item, { selected: !item.selected })} /><span /></label><button className="highlight-select" onClick={() => selectHighlight(item)}><span className="highlight-time"><Play size={13} fill="currentColor" />{formatDuration(item.start)} — {formatDuration(item.end)}</span><strong>{item.title}</strong><small>{Math.round(item.confidence * 100)}% confidence · {item.analysis_method}</small></button></div>
            {selectedId === item.id && <div className="highlight-edit"><Field label="Reel title"><input value={item.title} maxLength={180} onChange={event => setHighlights(current => current.map(h => h.id === item.id ? { ...h, title: event.target.value } : h))} onBlur={() => void updateHighlight(item, { title: item.title })} /></Field>
              <div className="field-row"><Field label="Start (seconds)"><input type="number" min={0} step={0.1} value={item.start} onChange={event => setHighlights(current => current.map(h => h.id === item.id ? { ...h, start: Number(event.target.value) } : h))} onBlur={() => void updateHighlight(item, { start: clamp(item.start, 0, item.end - 0.1) })} /></Field><Field label="End (seconds)"><input type="number" min={0.1} step={0.1} value={item.end} onChange={event => setHighlights(current => current.map(h => h.id === item.id ? { ...h, end: Number(event.target.value) } : h))} onBlur={() => void updateHighlight(item, { end: Math.max(item.start + 0.1, item.end) })} /></Field></div>
              <p>{item.explanation}</p><blockquote>{item.transcript_excerpt}</blockquote>
            </div>}
          </article>)}</div>}
        </div>
        {selectedHighlights.length > 0 && <div className="panel export-panel"><span className="eyebrow">04 / EXPORT</span><h2>Vertical output · {selectedHighlights.length} reel{selectedHighlights.length > 1 ? 's' : ''}</h2><Field label="Platform preset"><select value={preset} onChange={event => setPreset(event.target.value as typeof preset)}><option value="youtube">YouTube Shorts · up to 3 min</option><option value="instagram">Instagram Reels · up to 90 sec</option><option value="facebook">Facebook Reels · up to 90 sec</option></select></Field>
          <div className="field-row"><Field label="Fit"><select value={fitMode} onChange={event => setFitMode(event.target.value as typeof fitMode)}><option value="crop">Crop to fill</option><option value="pad">Pad to fit</option></select></Field><Field label="Quality"><select value={quality} onChange={event => setQuality(event.target.value as typeof quality)}><option value="draft">Draft</option><option value="medium">Medium</option><option value="high">High</option></select></Field></div>
          <label className="toggle-label export-toggle"><input type="checkbox" checked={burnSubtitles} disabled={!transcript} onChange={event => setBurnSubtitles(event.target.checked)} /><span><Captions size={15} />Burn in subtitles</span></label><div className="output-spec"><span>1080 × 1920</span><span>H.264 + AAC</span><span>{selectedHighlights.length} clip{selectedHighlights.length > 1 ? 's' : ''}</span></div>
          <button className="button primary full" disabled={busy === 'create'} onClick={() => void create(true)}><Clapperboard size={16} />{busy === 'create' ? 'Creating…' : `Create & render ${selectedHighlights.length} reel${selectedHighlights.length > 1 ? 's' : ''}`}</button><button className="button ghost full" disabled={busy === 'create'} onClick={() => void create(false)}><Scissors size={15} />Save {selectedHighlights.length} draft{selectedHighlights.length > 1 ? 's' : ''}</button>
        </div>}
      </aside>
    </div>
  </div>
}
