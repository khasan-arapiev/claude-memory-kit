# Hosting

## FTP Access

The FTP root is `public_html`. Use relative paths only.
Credentials live in workspace-root `Security/project.json` under the `ftp` key.
The FTP password is rotated every 90 days.

## SSL Certificates

Let's Encrypt auto-renews every 60 days via the host's cron.
Manual renewal command lives in the deploy script.

## DNS

Records are managed in Cloudflare. The apex points to the host IP.
