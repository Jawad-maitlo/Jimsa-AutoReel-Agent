import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Clapperboard, FileUp, Film, Folder, MoreHorizontal, Pencil, Play, Plus, Search, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { EmptyState, Modal, Spinner, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { api, json, mediaUrl, uploadVideo } from '@/lib/api'
import { formatBytes, formatDuration } from '@/lib/format'
import type { Video } from '@/types'

export default function Library() {
  const { projects, videos, selectedProjectId, setSelectedProjectId, setSelectedVideoId, navigate, refresh, notify } = useApp()
  const [query, setQuery] = useState(''); const [uploading, setUploading] = useState(false); const [dragging, setDragging] = useState(false)
  const [projectModal, setProjectModal] = useState<'new' | 'rename' | null>(null); const [projectName, setProjectName] = useState('')
  const [preview, setPreview] = useState<Video | null>(null); const [deleteTarget, setDeleteTarget] = useState<'project' | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const currentProject = projects.find(project => project.id === selectedProjectId)
  const filtered = videos.filter(video => (!selectedProjectId || video.project_id === selectedProjectId) && video.original_name.toLowerCase().includes(query.toLowerCase()))

  const importFiles = async (files: FileList | File[]) => {
    if (!selectedProjectId) { notify('Create a project before importing video', 'error'); return }
    const file = files[0]; if (!file) return
    setUploading(true)
    try { const video = await api<Video>('/videos/import', uploadVideo(selectedProjectId, file)); await refresh(); setSelectedVideoId(video.id); notify(`Imported ${video.original_name}`, 'success') }
    catch (error) { notify(error instanceof Error ? error.message : 'Import failed', 'error') }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = '' }
  }
  const saveProject = async (event: FormEvent) => {
    event.preventDefault(); if (!projectName.trim()) return
    try {
      if (projectModal === 'new') { const project = await api<{ id: number }>('/projects', json('POST', { name: projectName })); setSelectedProjectId(project.id) }
      else if (selectedProjectId) await api(`/projects/${selectedProjectId}`, json('PATCH', { name: projectName }))
      await refresh(); setProjectModal(null); setProjectName(''); notify('Project saved', 'success')
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not save project', 'error') }
  }
  const deleteProject = async () => {
    if (!selectedProjectId) return
    try { await api(`/projects/${selectedProjectId}?delete_files=false`, json('DELETE')); setSelectedProjectId(null); await refresh(); setDeleteTarget(null); notify('Project removed; source files were kept on disk', 'success') }
    catch (error) { notify(error instanceof Error ? error.message : 'Delete failed', 'error') }
  }
  return <div className="page">
    <PageHeader eyebrow="MEDIA / LIBRARY" title="Source library" description="Organize long-form recordings into projects. Originals stay untouched on disk."
      actions={<button className="button primary" disabled={uploading || !selectedProjectId} onClick={() => fileInput.current?.click()}>{uploading ? <Spinner label="Importing" /> : <><Upload size={17} />Import video</>}</button>} />
    <input ref={fileInput} className="visually-hidden" type="file" accept=".mp4,.mov,.mkv,.webm,.m4v,video/*" onChange={(event: ChangeEvent<HTMLInputElement>) => event.target.files && void importFiles(event.target.files)} />
    <div className="library-layout">
      <aside className="project-rail"><div className="section-heading"><span className="eyebrow">PROJECTS</span><button className="icon-button" onClick={() => { setProjectName(''); setProjectModal('new') }} aria-label="New project"><Plus size={18} /></button></div>
        <button className={`project-item ${selectedProjectId === null ? 'active' : ''}`} onClick={() => setSelectedProjectId(null)}><Folder size={17} /><span>All videos</span><b>{videos.length}</b></button>
        {projects.map(project => <button key={project.id} className={`project-item ${selectedProjectId === project.id ? 'active' : ''}`} onClick={() => setSelectedProjectId(project.id)}><Folder size={17} /><span>{project.name}</span><b>{project.video_count}</b></button>)}
        {currentProject && <div className="project-tools"><button onClick={() => { setProjectName(currentProject.name); setProjectModal('rename') }}><Pencil size={14} />Rename</button><button className="danger-text" onClick={() => setDeleteTarget('project')}><Trash2 size={14} />Delete</button></div>}
      </aside>
      <section className="library-content">
        <div className="library-toolbar"><label className="search-box"><Search size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search source videos" aria-label="Search source videos" />{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={15} /></button>}</label><span>{filtered.length} video{filtered.length === 1 ? '' : 's'}</span></div>
        <div className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); void importFiles(event.dataTransfer.files) }}>
          <FileUp size={22} /><span><strong>Drop a video to import</strong> or use the file picker</span><small>MP4 · MOV · MKV · WEBM · M4V</small>
        </div>
        {filtered.length === 0 ? <EmptyState icon={<Film />} title={query ? 'No matching videos' : 'No source videos yet'} description={query ? 'Try another filename or clear the search.' : 'Import a recording to extract its story, transcript, and best short-form moments.'} /> :
          <div className="video-grid">{filtered.map(video => <article className="video-card" key={video.id}>
            <button className="video-poster" onClick={() => setPreview(video)} aria-label={`Preview ${video.original_name}`}>{video.thumbnail_url ? <img src={mediaUrl(video.thumbnail_url)} alt="" /> : <Film size={40} />}<span className="play-disc"><Play size={19} fill="currentColor" /></span><b>{formatDuration(video.duration)}</b></button>
            <div className="video-info"><div><strong title={video.original_name}>{video.original_name}</strong><StatusPill status={video.status} /></div><p>{video.width}×{video.height} · {video.frame_rate.toFixed(1)} fps · {formatBytes(video.file_size)}</p>
              <div className="video-actions"><button className="button secondary" onClick={() => { setSelectedVideoId(video.id); navigate('create') }}><Sparkles size={15} />Create reel</button><button className="icon-button" onClick={() => setPreview(video)} aria-label="Open preview"><MoreHorizontal size={18} /></button></div>
            </div>
          </article>)}</div>}
      </section>
    </div>
    {projectModal && <Modal title={projectModal === 'new' ? 'Create project' : 'Rename project'} onClose={() => setProjectModal(null)}><form onSubmit={saveProject} className="form-stack"><label className="field"><span className="field-label">Project name</span><input autoFocus required maxLength={120} value={projectName} onChange={event => setProjectName(event.target.value)} placeholder="e.g. Podcast season one" /></label><div className="modal-actions"><button type="button" className="button secondary" onClick={() => setProjectModal(null)}>Cancel</button><button className="button primary" type="submit">Save project</button></div></form></Modal>}
    {preview && <Modal title={preview.original_name} onClose={() => setPreview(null)} wide><video className="preview-video" src={mediaUrl(preview.stream_url)} controls autoPlay playsInline /><div className="preview-meta"><span>{formatDuration(preview.duration)}</span><span>{preview.width}×{preview.height}</span><span>{preview.has_audio ? `Audio: ${preview.audio_codec}` : 'No audio stream'}</span></div><button className="button primary full" onClick={() => { setSelectedVideoId(preview.id); setPreview(null); navigate('create') }}><Clapperboard size={16} />Create from this video</button></Modal>}
    {deleteTarget && <Modal title="Delete project?" onClose={() => setDeleteTarget(null)}><p className="modal-copy">This removes the project and its database records. Source and rendered media files are kept on disk.</p><div className="modal-actions"><button className="button secondary" onClick={() => setDeleteTarget(null)}>Cancel</button><button className="button danger" onClick={() => void deleteProject()}>Delete project</button></div></Modal>}
  </div>
}
