# GlitchHunter Docker Deployment Guide

## 🚀 Schnellstart

### 1. Repository klonen
```bash
git clone https://github.com/glitchhunter/glitchhunter.git
cd glitchhunter
```

### 2. Build & Start
```bash
# Build (ca. 1-2 Minuten, Image-Größe: ~864MB)
bash scripts/docker_build.sh

# Start
bash scripts/docker_start.sh
```

### 3. Öffnen
- Dashboard: http://localhost:6262
- API Docs: http://localhost:6262/docs

> **Hinweis:** Das Docker Image enthält die Web-UI mit allen Backend-Services. Für volle Funktionalität (ML, Swarm, etc.) werden zusätzliche Services oder Remote-APIs benötigt.

---

## 📋 Alternative: Docker Compose

```bash
# Start
docker compose up -d

# Logs
docker compose logs -f

# Stop
docker compose down

# Neustart
docker compose restart
```

---

## 📋 Alternative: Docker Run

```bash
# Start
docker run -d \
    --name glitchhunter \
    -p 6262:6262 \
    -v $(pwd)/config.yaml:/app/config.yaml:ro \
    -v gh-data:/app/data \
    -v gh-logs:/app/logs \
    -v gh-cache:/app/cache \
    -v gh-reports:/app/reports \
    --restart unless-stopped \
    glitchhunter:latest

# Logs
docker logs -f glitchhunter

# Stop
docker stop glitchhunter
docker rm glitchhunter
```

---

## ⚙️ Konfiguration

### config.yaml anpassen

```bash
# Kopiere config.yaml
cp config.yaml config.custom.yaml

# Bearbeiten
nano config.custom.yaml

# Mit custom Config starten
docker run -d \
    -p 6262:6262 \
    -v $(pwd)/config.custom.yaml:/app/config.yaml:ro \
    glitchhunter:latest
```

### API-Keys setzen

```bash
# Via Environment Variables
docker run -d \
    -p 6262:6262 \
    -e OPENAI_API_KEY=sk-... \
    -e ANTHROPIC_API_KEY=sk-ant-... \
    -e DEEPSEEK_API_KEY=... \
    glitchhunter:latest
```

---

## 📁 Volumes

| Volume | Pfad | Inhalt |
|--------|------|--------|
| `gh-data` | `/app/data` | Settings, History, Problems |
| `gh-logs` | `/app/logs` | Log-Dateien |
| `gh-cache` | `/app/cache` | API-Cache, Response-Cache |
| `gh-reports` | `/app/reports` | Generierte Reports |

**Backup:**
```bash
# Volumes sichern
docker run --rm -v gh-data:/data -v $(pwd):/backup alpine tar czf /backup/gh-data-backup.tar.gz -C /data .

# Volumes wiederherstellen
docker run --rm -v gh-data:/data -v $(pwd):/backup alpine tar xzf /backup/gh-data-backup.tar.gz -C /data
```

---

## 🔧 Erweiterte Konfiguration

### Ressourcen-Limits

```yaml
# docker-compose.yml
services:
  glitchhunter:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 2G
```

### GPU-Support (optional)

```yaml
# docker-compose.yml
services:
  glitchhunter:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name glitchhunter.example.com;

    location / {
        proxy_pass http://localhost:6262;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🐛 Troubleshooting

### Container startet nicht
```bash
# Logs prüfen
docker logs glitchhunter

# Port-Konflikt prüfen
lsof -i :6262

# Container neu starten
docker restart glitchhunter
```

### Performance-Probleme
```bash
# Ressourcen-Usage prüfen
docker stats glitchhunter

# Logs prüfen
docker logs glitchhunter 2>&1 | grep -i error
```

### Daten verloren
```bash
# Volumes prüfen
docker volume ls | grep gh-

# Volume-Inhalt prüfen
docker run --rm -v gh-data:/data -it alpine ls -la /data
```

---

## 🔄 Updates

```bash
# Neueste Version pullen
git pull

# Neu bauen
bash scripts/docker_build.sh

# Container neu starten
bash scripts/docker_start.sh
```

---

## 📊 Monitoring

```bash
# Container-Status
docker ps -f name=glitchhunter

# Logs
docker logs -f glitchhunter

# Ressourcen
docker stats glitchhunter

# Health-Check
curl http://localhost:6262/api/v1/status
```

---

## 🗑️ Cleanup

```bash
# Container stoppen und entfernen
bash scripts/docker_stop.sh

# Volumes löschen (ALLE DATEN WEG!)
docker volume rm gh-data gh-logs gh-cache gh-reports

# Image löschen
docker rmi glitchhunter:latest glitchhunter:v3.0
```

---

## 🌐 Deployment auf Remote-Host

### 1. Image exportieren
```bash
# Image als TAR speichern
docker save glitchhunter:latest -o glitchhunter.tar

# Auf Remote-Host kopieren
scp glitchhunter.tar user@remote-host:/tmp/
```

### 2. Auf Remote-Host importieren
```bash
# Image laden
docker load -i /tmp/glitchhunter.tar

# Starten
docker run -d \
    --name glitchhunter \
    -p 6262:6262 \
    -v gh-data:/app/data \
    --restart unless-stopped \
    glitchhunter:latest
```

### 3. Fertig!
- Dashboard: http://remote-host:6262
