# Official social API setup

Local reel generation and MP4 export need none of these credentials. Live publishing was not credential-tested in the delivery environment. The adapters use official OAuth and publishing endpoints and surface real API errors.

## Common local redirect

Register this exact URL in each developer application:

```text
http://127.0.0.1:8000/api/social/oauth/callback
```

If you change `APP_BASE_URL`, update the registered redirect to match. Do not put client secrets in frontend environment variables or source files.

## YouTube Shorts — Google Cloud / YouTube Data API v3

1. Create a Google Cloud project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen, add yourself as a test user while in testing mode, and create **Web application** OAuth credentials.
3. Add the common local redirect above.
4. Set in `.env`:

   ```dotenv
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

5. Restart the API, open **Social accounts → Connect YouTube Shorts**, and authorize a channel you control.

Requested scopes are `youtube.upload` and `youtube.readonly`. The adapter reads the authorized channel, uploads through the official resumable `videos` endpoint, and stores the returned video ID. YouTube scheduling uses a future `publishAt` with private visibility. Token refresh uses the stored encrypted refresh token. Google verification or additional review may be required for broader production use.

Official references: `https://developers.google.com/youtube/v3/docs/videos/insert` and `https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps`.

## Instagram Reels — Instagram Graph API

1. Create a Meta developer app suitable for Facebook Login and Instagram Graph API use.
2. Use an Instagram **Business or Creator** account linked to a Facebook Page you manage.
3. Configure the common local redirect and request the permissions needed by the integration: `pages_show_list`, `pages_manage_posts`, `instagram_content_publish`, and `business_management`.
4. Complete any required Meta app review and add authorized testers while developing.
5. Set in `.env`:

   ```dotenv
   META_APP_ID=your-app-id
   META_APP_SECRET=your-app-secret
   META_GRAPH_VERSION=v23.0
   PUBLIC_MEDIA_BASE_URL=https://media.example.com/reels
   ```

6. Host the contents of `storage/reels` at that public HTTPS base URL. For example, `https://media.example.com/reels/reel_1.mp4` must return the exact rendered MP4 without authentication or an expiring link during processing.
7. Restart and connect. The OAuth callback discovers Instagram professional accounts linked to authorized Pages.

The adapter creates a `REELS` media container with `video_url`, polls `status_code` until `FINISHED`, then calls `media_publish`. It never skips processing or treats container creation as publication. This integration supports publish-now only; schedule through an official Meta scheduling tool instead.

Official reference: `https://developers.facebook.com/docs/instagram-platform/content-publishing`.

## Facebook Reels — Facebook Graph API

1. Configure the same Meta app credentials as above (a separate app is also fine).
2. Use a Facebook Page you manage and request `pages_show_list`, `pages_manage_posts`, and `pages_read_engagement`.
3. Complete required permissions/app review, then connect through **Social accounts**.

The adapter performs the official `/{page-id}/video_reels` phases: `start`, binary upload to the returned upload URL, and `finish`. It stores the returned video ID only after confirmation. Future scheduling uses `video_state=SCHEDULED` and `scheduled_publish_time`; platform timing restrictions still apply and API errors remain visible.

Official reference: `https://developers.facebook.com/docs/video-api/guides/reels-publishing`.

## Version maintenance

Graph API versions and permission requirements can change. `META_GRAPH_VERSION` is configurable. Before upgrading it, review Meta’s current official references and test against a development account. No platform approval, app review, token, or public media host is included in this project.
