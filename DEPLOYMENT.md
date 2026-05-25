# NUNBot Deployment Guide

## Target production layout

- **Source repo:** `/home/diegol/apps/nunbot`
- **Deployment root:** `/opt/nunbot`
- **Application container port:** `8501`
- **Host loopback port for Nginx:** `127.0.0.1:8502`
- **Public domain:** `https://nunbot.myserverlongstaff.com`

## Runtime requirements

- Docker Engine already installed on the server
- Docker Compose plugin
- Nginx reverse proxy already running on the host
- Let's Encrypt certificate for `nunbot.myserverlongstaff.com`
- `OPENAI_API_KEY` available in `/opt/nunbot/.env`

## Deployment approach

NUNBot is deployed as a Docker Compose stack under `/opt/nunbot` with:

- immutable image build from the repository
- `restart: unless-stopped` for boot persistence
- Nginx proxying HTTPS traffic to `127.0.0.1:8502`
- no bind mount of the source tree in production

## Initial deployment

```bash
cd /opt/nunbot
cp .env.example .env   # then edit OPENAI_API_KEY
docker compose up -d --build
```

Then ensure the Nginx site is using `nginx/nunbot.conf` as the source of truth and reload Nginx.

## Validate the stack

```bash
docker compose ps
docker compose logs --tail=100
curl -I http://127.0.0.1:8502/
```

Then validate HTTPS externally:

```bash
curl -I https://nunbot.myserverlongstaff.com/
```

## Nginx config

Use the file in `nginx/nunbot.conf` as the source of truth.

Important proxy settings:

- `proxy_http_version 1.1`
- `Upgrade` / `Connection` headers for WebSocket support
- `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`
- long read/send timeouts
- existing certificate paths under `/etc/letsencrypt/live/nunbot.myserverlongstaff.com/`

After changing Nginx:

```bash
nginx -t
systemctl reload nginx
```

## Startup persistence

The container uses `restart: unless-stopped`, so Docker will bring it back automatically after host reboot as long as Docker starts normally.

## Update workflow

1. Pull or sync the newest code into `/opt/nunbot`.
2. Rebuild the image:

```bash
cd /opt/nunbot
docker compose up -d --build
```

3. Watch logs if needed:

```bash
docker compose logs -f
```

4. Re-check the HTTP and HTTPS endpoints.

## Rollback workflow

If the new version misbehaves:

```bash
cd /opt/nunbot
git log --oneline --decorate -n 5
git checkout <previous-commit>
docker compose up -d --build
```

If the issue is only in the container image, you can also restore the previous image tag if it was retained locally.

## Backup / safety notes

- Keep `/etc/nginx/sites-available/nunbot` backed up before edits.
- Do not remove the existing certificate files; Nginx depends on them.
- Do not touch Immich, Heimdall, Wake, or SSH configuration.
- Keep the source repo and deployment root cleanly separated.
