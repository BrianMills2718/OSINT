# Production Deployment Guide

**Target**: Small investigative journalism team (3-10 users)
**Infrastructure**: Single VPS with Docker Compose + PostgreSQL
**Cost**: ~$20-40/month
**Setup Time**: ~2 hours

---

## Prerequisites

1. **VPS Server**:
   - Provider: DigitalOcean, Linode, Vultr, or Hetzner
   - Specs: 4GB RAM, 2 CPUs, 80GB SSD (minimum)
   - OS: Ubuntu 22.04 LTS
   - Cost: $20-40/month

2. **Domain Name**:
   - Example: `research.yournewsroom.com`
   - DNS A record pointing to your VPS IP

3. **Required Credentials**:
   - API keys (.env file)
   - PostgreSQL password

---

## Step 1: Server Setup (30 minutes)

### SSH into your server:
```bash
ssh root@your-server-ip
```

### Install Docker:
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Start Docker
systemctl enable docker
systemctl start docker

# Verify
docker --version
docker compose version
```

### Create app user (security):
```bash
adduser sigint
usermod -aG docker sigint
su - sigint
```

---

## Step 2: Clone & Configure (15 minutes)

### Clone repository:
```bash
cd ~
git clone <your-repo-url> sigint-research
cd sigint-research
```

### Create production .env:
```bash
cat > .env << 'EOF'
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Data Source API Keys
BRAVE_API_KEY=...
DISCORD_TOKEN=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
# ... other keys

# Database
POSTGRES_PASSWORD=<generate-strong-password>
DATABASE_URL=postgresql://sigint:$POSTGRES_PASSWORD@postgres:5432/sigint_research
EOF

chmod 600 .env  # Secure it
```

### Update nginx config:
```bash
# Edit nginx/nginx.conf
nano nginx/nginx.conf

# Replace research.example.com with your actual domain
:%s/research.example.com/research.yournewsroom.com/g
```

---

## Step 3: SSL Certificate (15 minutes)

### Install Certbot:
```bash
apt install certbot -y
```

### Get SSL certificate:
```bash
# Stop any services on port 80
docker compose -f docker-compose.prod.yml down

# Get certificate
certbot certonly --standalone -d research.yournewsroom.com

# Certificates saved to:
# /etc/letsencrypt/live/research.yournewsroom.com/
```

### Auto-renewal (cron job):
```bash
crontab -e

# Add this line (renew monthly):
0 0 1 * * certbot renew --quiet && docker compose -f docker-compose.prod.yml restart nginx
```

---

## Step 4: Database Setup (10 minutes)

### Create database schema:
```bash
# Start just PostgreSQL first
docker compose -f docker-compose.prod.yml up -d postgres

# Wait for it to be healthy
docker compose -f docker-compose.prod.yml ps

# Create schema (we'll create this file later)
docker compose -f docker-compose.prod.yml exec postgres psql -U sigint -d sigint_research -f /app/schema.sql
```

---

## Step 5: Deploy (10 minutes)

### Build and start all services:
```bash
# Build images
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# Expected output:
# NAME                STATUS              PORTS
# sigint-postgres     Up (healthy)        127.0.0.1:5432->5432/tcp
# sigint-research     Up
# sigint-web          Up                  127.0.0.1:8501->8501/tcp
# sigint-nginx        Up                  0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# sigint-backup       Up
```

### Test it:
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs -f web

# Visit in browser:
https://research.yournewsroom.com
```

---

## Step 6: Backups (10 minutes)

### Verify automated backups:
```bash
# Check backup directory
ls -lh backups/

# Should see:
# backup_20251122_020000.sql.gz

# Test restore:
gunzip -c backups/backup_20251122_020000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U sigint sigint_research
```

### Optional: S3 backup sync:
```bash
# Install AWS CLI
apt install awscli -y

# Configure S3
aws configure

# Add to crontab:
0 3 * * * aws s3 sync ~/sigint-research/backups s3://your-bucket/backups/
```

---

## Step 7: Monitoring (10 minutes)

### View logs:
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f postgres
```

### Resource usage:
```bash
# Container stats
docker stats

# Disk usage
df -h
du -sh ~/sigint-research/data
```

### Health checks:
```bash
# Check if services are running
docker compose -f docker-compose.prod.yml ps

# Check PostgreSQL health
docker compose -f docker-compose.prod.yml exec postgres pg_isready
```

---

## Step 8: Security Hardening (20 minutes)

### Firewall:
```bash
# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Verify
ufw status
```

### SSH hardening:
```bash
nano /etc/ssh/sshd_config

# Change these:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
systemctl restart sshd
```

### Fail2ban (optional):
```bash
apt install fail2ban -y
systemctl enable fail2ban
systemctl start fail2ban
```

---

## Maintenance

### Update application:
```bash
cd ~/sigint-research
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Restart services:
```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart web
```

### View backups:
```bash
ls -lh backups/
```

### Restore from backup:
```bash
BACKUP_FILE=backups/backup_20251122_020000.sql.gz
gunzip -c $BACKUP_FILE | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U sigint sigint_research
```

---

## Troubleshooting

### Service won't start:
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs <service-name>

# Check resource usage
docker stats
free -h
df -h
```

### Database connection issues:
```bash
# Test connection
docker compose -f docker-compose.prod.yml exec postgres psql -U sigint -d sigint_research

# Check PostgreSQL logs
docker compose -f docker-compose.prod.yml logs postgres
```

### Web UI not accessible:
```bash
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx

# Test Streamlit directly
curl http://localhost:8501

# Check firewall
ufw status
```

---

## Cost Breakdown (Monthly)

| Item | Cost |
|------|------|
| VPS (4GB RAM, 2 CPU) | $20-40 |
| Domain name | $1-2 |
| LLM API usage (Gemini Flash) | $2-10 |
| **Total** | **$23-52/month** |

**For 5 users**: ~$5-10/user/month

---

## Scaling (When You Grow)

### 10-50 users:
- Upgrade VPS to 8GB RAM ($40-80/month)
- Add Redis for caching
- Consider managed PostgreSQL (DigitalOcean Managed DB)

### 50+ users:
- Multi-server setup (app servers + DB server)
- Load balancer
- Kubernetes or Docker Swarm
- Consider professional DevOps help

---

## Support & Documentation

- **Logs**: `docker compose -f docker-compose.prod.yml logs`
- **Status**: `docker compose -f docker-compose.prod.yml ps`
- **Restart**: `docker compose -f docker-compose.prod.yml restart`
- **Update**: `git pull && docker compose -f docker-compose.prod.yml up -d --build`

Need help? Check documentation or reach out to team.
