# Playing away from home

The game serves plain HTTP on port 8000. Pick one:

## 1. A VPN (simplest, safest)

Install [Tailscale](https://tailscale.com/) (or WireGuard) on the server and on everyone's phones. Then everyone opens `http://<server-tailscale-name>:8000` from anywhere, and nothing is exposed to the internet.

## 2. A reverse proxy with HTTPS

If you already run one (SWAG, Nginx Proxy Manager, Caddy, Traefik), point a subdomain at the game's port 8000. Only the game needs a route; abs-stats stays internal.

Example for SWAG / nginx (`dungeon.subdomain.conf`):

```nginx
server {
    listen 443 ssl;
    server_name dungeon.*;
    include /config/nginx/ssl.conf;
    client_max_body_size 2m;

    # Admin pages: home network only (adjust to your LAN ranges)
    location ~* (admin|^/radar/api/) {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        include /config/nginx/proxy.conf;
        proxy_pass http://YOUR-SERVER-IP:8000;
    }

    location / {
        include /config/nginx/proxy.conf;
        proxy_pass http://YOUR-SERVER-IP:8000;
    }
}
```

Caddy:

```
dungeon.example.com {
    reverse_proxy YOUR-SERVER-IP:8000
}
```

Tips:
- Set a strong admin password; logins lock out after repeated wrong guesses.
- Players log in with a 4-digit PIN. That's fine on a VPN; on the open internet, consider an extra login layer in your proxy (basic auth, Authelia, Cloudflare Access).
- Never forward port 8000 or abs-stats' port 3000 straight to the internet.
