export type PageId = 'dashboard' | 'library' | 'create' | 'reels' | 'processing' | 'publishing' | 'accounts' | 'settings'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface Project { id: number; name: string; created_at: string; updated_at: string; video_count: number }
export interface Video {
  id: number; project_id: number; original_name: string; file_size: number; duration: number
  width: number; height: number; frame_rate: number; has_audio: boolean; audio_codec: string | null
  status: string; error: string | null; created_at: string; thumbnail_url: string | null; stream_url: string
}
export interface Segment { id: number; start: number; end: number; text: string }
export interface Transcript { id: number; video_id: number; language: string | null; model: string; text: string; segments: Segment[] }
export interface Highlight {
  id: number; video_id: number; start: number; end: number; title: string; explanation: string
  confidence: number; transcript_excerpt: string; analysis_method: string; selected: boolean
}
export interface Reel {
  id: number; video_id: number; highlight_id: number | null; title: string; description: string; hashtags: string
  subtitles_text: string; cover_timestamp: number; start: number; end: number; preset: 'youtube' | 'instagram' | 'facebook'
  width: number; height: number; quality: 'draft' | 'medium' | 'high'; fit_mode: 'crop' | 'pad'; burn_subtitles: boolean
  status: string; error: string | null; created_at: string; updated_at: string; output_url: string | null
}
export interface ProcessingJob {
  id: string; kind: string; entity_id: number; status: JobStatus; progress: number; stage: string
  error: string | null; cancel_requested: boolean; created_at: string; updated_at: string
}
export interface SocialAccount {
  id: number; platform: 'youtube' | 'instagram' | 'facebook'; platform_account_id: string; display_name: string
  token_expires_at: string | null; scopes: string; status: string
}
export interface PublishJob {
  id: number; reel_id: number; account_id: number; platform: string; status: string; scheduled_at: string | null
  platform_post_id: string | null; platform_url: string | null; error: string | null; attempts: number
  created_at: string; published_at: string | null; reel_title: string; account_name: string
}
export interface SystemStatus {
  ffmpeg: string | null; ffprobe: string | null
  ollama: { available: boolean; message: string; models: string[] }
  whisper: { model: string; device: string; compute_type: string }
  storage: { path: string; free_gb: number }
  credentials: { google: boolean; meta: boolean }
}
export interface AppSettings {
  whisper_model: string; whisper_device: string; whisper_compute_type: string; ollama_endpoint: string
  ollama_model: string; public_media_base_url: string; max_upload_mb: number
}
