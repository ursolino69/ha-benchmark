# Security and privacy model

- The Home Assistant app accepts HTTP requests only from the Supervisor ingress address or loopback.
- State-changing app requests require an additional request header.
- Publishing is opt-in and preceded by an exact JSON preview.
- Local device names, platform strings, entity IDs, credentials and Home Assistant states are excluded.
- The community service validates and recalculates scores; client-provided scores are not trusted.
- The public service binds to loopback and is exposed only through the dedicated TLS virtual host.
- Public text fields are length/control-character checked and HTML-escaped by the browser client.
- Uploads are limited to 64 KiB and 20 write attempts per keyed IP hash per hour.
- Raw IP addresses are not stored by the application and Apache access logs are disabled for this host.
- Deletion tokens have 256 bits of randomness; only their SHA-256 hashes are stored server-side.
- The admin token is a random 256-bit secret readable only by root and the service group.
- The systemd unit uses an unprivileged user and filesystem/kernel hardening.
- Database snapshots are retained for seven days; deletion tombstones survive database restoration.

## Reporting

Do not publish a security issue or deletion key. Contact the operator address shown on
`https://benchmark.smartdomo.de/privacy.html` with a minimal reproduction and affected version.
