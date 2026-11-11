import { useState } from 'react'
import { Facebook, Instagram, KeyRound, Link2, ShieldCheck, Trash2, Youtube } from 'lucide-react'
import { PageHeader } from '@/components/Layout'
import { Modal, StatusPill } from '@/components/UI'
import { useApp } from '@/context/AppContext'
import { api, json } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { SocialAccount } from '@/types'

const platforms = [
  { id: 'youtube', name: 'YouTube Shorts', icon: Youtube, description: 'Resumable YouTube Data API uploads, with official scheduling support.', scope: 'youtube.upload · youtube.readonly', color: 'red' },
  { id: 'instagram', name: 'Instagram Reels', icon: Instagram, description: 'Graph API media containers for Business or Creator accounts.', scope: 'instagram_content_publish · pages_manage_posts', color: 'pink' },
  { id: 'facebook', name: 'Facebook Reels', icon: Facebook, description: 'Three-phase Graph API uploads to authorized Facebook Pages.', scope: 'pages_manage_posts · pages_read_engagement', color: 'blue' },
] as const

export default function Accounts() {
  const { accounts, status, refresh, notify } = useApp(); const [disconnect, setDisconnect] = useState<SocialAccount | null>(null); const [connecting, setConnecting] = useState('')
  const connect = async (platform: string) => { setConnecting(platform); try { const result = await api<{ authorization_url: string }>(`/social/oauth/${platform}/start`); const popup = window.open(result.authorization_url, '_blank', 'width=680,height=760'); if (!popup) notify('Allow the pop-up or open the returned OAuth URL to continue', 'info') } catch (error) { notify(error instanceof Error ? error.message : 'Could not start OAuth', 'error') } finally { setConnecting('') } }
  const remove = async () => { if (!disconnect) return; try { await api(`/social/accounts/${disconnect.id}`, json('DELETE')); setDisconnect(null); await refresh(); notify('Account disconnected and encrypted tokens removed', 'success') } catch (error) { notify(error instanceof Error ? error.message : 'Disconnect failed', 'error') } }
  return <div className="page"><PageHeader eyebrow="DISTRIBUTION / CONNECTIONS" title="Social accounts" description="Connect only through official OAuth. Tokens are encrypted at rest and never written to application logs." />
    <div className="security-banner"><ShieldCheck /><div><strong>Credentials stay in your local configuration</strong><p>No app secrets are included in the project. Platform approval, permissions, and eligible accounts are still required.</p></div></div>
    <div className="platform-grid">{platforms.map(platform => { const Icon = platform.icon; const connected = accounts.filter(account => account.platform === platform.id); const configured = platform.id === 'youtube' ? status?.credentials.google : status?.credentials.meta; return <section className="platform-panel panel" key={platform.id}><div className="platform-heading"><Icon className={platform.color} /><div><span className="eyebrow">OFFICIAL API</span><h2>{platform.name}</h2></div><span className={`config-dot ${configured ? 'ready' : ''}`} title={configured ? 'Credentials configured' : 'Credentials missing'} /></div><p>{platform.description}</p><code>{platform.scope}</code>
      <div className="connected-list">{connected.length === 0 ? <span className="quiet">No connected accounts</span> : connected.map(account => <div className="connected-account" key={account.id}><span className="account-avatar">{account.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{account.display_name}</strong><small>{account.token_expires_at ? `Token expiry: ${formatDate(account.token_expires_at)}` : 'Token expiry managed by platform'}</small></div><StatusPill status={account.status} /><button className="icon-button" onClick={() => setDisconnect(account)} aria-label={`Disconnect ${account.display_name}`}><Trash2 size={15} /></button></div>)}</div>
      <button className="button secondary full" disabled={connecting === platform.id} onClick={() => void connect(platform.id)}><Link2 size={16} />{connecting === platform.id ? 'Preparing OAuth…' : connected.length ? 'Connect another account' : `Connect ${platform.name}`}</button>
    </section>})}</div>
    <section className="panel setup-panel"><span className="eyebrow">BEFORE YOU CONNECT</span><h2>Developer setup is explicit</h2><div className="setup-steps"><div><b>01</b><span><strong>Create developer apps</strong>Configure Google Cloud or Meta developer credentials in your own accounts.</span></div><div><b>02</b><span><strong>Add the local redirect</strong>Register <code>http://127.0.0.1:8000/api/social/oauth/callback</code>.</span></div><div><b>03</b><span><strong>Request permissions</strong>Complete any required app review and use eligible Business, Creator, Page, or channel accounts.</span></div></div><p className="setup-note"><KeyRound size={16} />Full credential and public-media instructions are included in <code>docs/SOCIAL_API.md</code>. Instagram also requires a public HTTPS URL for each rendered MP4.</p></section>
    {disconnect && <Modal title={`Disconnect ${disconnect.display_name}?`} onClose={() => setDisconnect(null)}><p className="modal-copy">This deletes the locally stored encrypted access and refresh tokens. It does not revoke access in the platform’s own security settings.</p><div className="modal-actions"><button className="button secondary" onClick={() => setDisconnect(null)}>Cancel</button><button className="button danger" onClick={() => void remove()}>Disconnect account</button></div></Modal>}
  </div>
}
