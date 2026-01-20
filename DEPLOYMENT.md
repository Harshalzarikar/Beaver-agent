# Production Deployment Guide

This guide covers deploying Beaver Agent to production environments.

## Pre-Deployment Checklist

- [ ] All environment variables configured in `.env`
- [ ] API keys validated and tested
- [ ] Redis instance provisioned
- [ ] PostgreSQL database created
- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] Monitoring alerts set up
- [ ] Backup strategy implemented
- [ ] Load testing completed

## Infrastructure Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: 100 Mbps

### Recommended for Production

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Network**: 1 Gbps
- **Load Balancer**: Nginx or AWS ALB
- **CDN**: CloudFlare or AWS CloudFront

## Deployment Options

### Option 1: Docker Compose (Single Server)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/beaver-agent.git
cd beaver-agent

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with production values

# 3. Start services
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/health

# 5. View logs
docker-compose logs -f api
```

### Option 2: Kubernetes

```bash
# 1. Create namespace
kubectl create namespace beaver-agent

# 2. Create secrets
kubectl create secret generic beaver-secrets \
  --from-literal=google-api-key=$GOOGLE_API_KEY \
  --from-literal=tavily-api-key=$TAVILY_API_KEY \
  -n beaver-agent

# 3. Apply manifests
kubectl apply -f k8s/ -n beaver-agent

# 4. Verify deployment
kubectl get pods -n beaver-agent
kubectl get svc -n beaver-agent
```

### Option 3: Cloud Platforms

#### AWS ECS

```bash
# 1. Build and push image
docker build -t beaver-agent:latest .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL
docker tag beaver-agent:latest $ECR_URL/beaver-agent:latest
docker push $ECR_URL/beaver-agent:latest

# 2. Create ECS task definition and service
# 2. Create ECS task definition and service
aws ecs create-service --cli-input-json file://ecs-service.json

### Option 4: Render.com (Recommended for ease of use)

We have included a `render.yaml` Blueprint for 1-click deployment.

1.  **Push to GitHub**: Ensure your code is in a public or private GitHub repository.
2.  **Create Blueprint**:
    *   Go to [dashboard.render.com/blueprints](https://dashboard.render.com/blueprints).
    *   Click "New Blueprint Instance".
    *   Connect your repository.
3.  **Configure Environment**:
    *   Render will detect `render.yaml`.
    *   It will ask for environment variables (API Keys).
    *   Fill in `GOOGLE_API_KEY`, `TAVILY_API_KEY`, and `REDIS_URL` (if using external Redis).
4.  **Deploy**: Click "Apply" to spin up both the API and UI services automatically.

```

## Environment Configuration

### Production Environment Variables

```bash
# Critical Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
API_KEYS=["prod-key-1","prod-key-2"]
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100

# Database
DATABASE_URL=postgresql://user:pass@prod-db:5432/beaver
DB_POOL_SIZE=20

# Redis
REDIS_URL=redis://prod-redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Monitoring
METRICS_ENABLED=true
LANGCHAIN_TRACING_V2=true
```

## Security Hardening

### 1. Network Security

```bash
# Firewall rules (UFW example)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 8000/tcp  # Block direct API access
sudo ufw enable
```

### 2. SSL/TLS Configuration

```nginx
# Nginx reverse proxy with SSL
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. API Key Rotation

```bash
# Generate new API keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update environment
# Add new key to API_KEYS array
# Remove old key after grace period
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'beaver-agent'
    static_configs:
      - targets: ['api:8000']
    
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alerts.yml'
```

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: beaver_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(emails_failed_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, email_processing_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "95th percentile latency > 5s"
```

## Backup Strategy

### Database Backups

```bash
# PostgreSQL backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U beaver beaver_db | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

### Redis Backups

```bash
# Redis backup (RDB snapshots)
redis-cli BGSAVE

# Copy snapshot
cp /var/lib/redis/dump.rdb /backups/redis/dump_$(date +%Y%m%d).rdb
```

## Scaling

### Horizontal Scaling

```bash
# Docker Compose scaling
docker-compose up -d --scale api=3

# Kubernetes scaling
kubectl scale deployment beaver-api --replicas=5 -n beaver-agent
```

### Load Balancer Configuration

```nginx
# Nginx load balancer
upstream beaver_backend {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    location / {
        proxy_pass http://beaver_backend;
    }
}
```

## Troubleshooting

### High Memory Usage

```bash
# Check container stats
docker stats

# Adjust worker count
API_WORKERS=2  # Reduce workers

# Increase memory limit
docker-compose up -d --scale api=2 --memory=2g
```

### Database Connection Pool Exhausted

```bash
# Increase pool size
DB_POOL_SIZE=50

# Check active connections
psql -U beaver -c "SELECT count(*) FROM pg_stat_activity;"
```

### Redis Connection Issues

```bash
# Check Redis status
redis-cli ping

# Monitor connections
redis-cli CLIENT LIST

# Increase max connections
REDIS_MAX_CONNECTIONS=100
```

## Rollback Procedure

```bash
# 1. Stop current deployment
docker-compose down

# 2. Restore previous version
git checkout <previous-tag>

# 3. Rebuild and deploy
docker-compose build
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/health
```

## Maintenance

### Regular Tasks

- **Daily**: Check logs for errors
- **Weekly**: Review metrics and performance
- **Monthly**: Update dependencies, rotate API keys
- **Quarterly**: Load testing, security audit

### Update Procedure

```bash
# 1. Backup current state
docker-compose exec postgres pg_dump -U beaver beaver_db > backup.sql

# 2. Pull latest changes
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Run migrations (if any)
# python manage.py migrate

# 5. Rebuild containers
docker-compose build

# 6. Rolling update
docker-compose up -d --no-deps --build api

# 7. Verify
curl http://localhost:8000/health
```

## Support

For production support:
- **Emergency**: support@yourcompany.com
- **Slack**: #beaver-agent-prod
- **On-call**: PagerDuty integration
