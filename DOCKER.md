# Y6 Practice Exam - Docker Deployment Guide

## Quick Start

### Option 1: Pull from Docker Hub (Recommended)

```bash
# Pull the latest image
docker pull ranaislek/y6-practice-exam:latest

# Run with simple compose (external database)
curl -O https://raw.githubusercontent.com/yourusername/y6-practice-exam/main/docker-compose.simple.yml
docker-compose -f docker-compose.simple.yml up -d
```

### Option 2: Full Stack (App + Database + Redis)

```bash
# Clone the repository
git clone https://github.com/yourusername/y6-practice-exam.git
cd y6-practice-exam

# Start everything
docker-compose up -d
```

## First-Time Setup

On first run, the setup wizard will automatically start:

```
╔═══════════════════════════════════════════════════════════╗
║           Y6 Practice Exam System                         ║
║           Spring Gate Private School                      ║
╚═══════════════════════════════════════════════════════════╝

Welcome to the Y6 Practice Exam System setup!

This wizard will help you configure:
  • Database connection (MySQL/MariaDB)
  • Email settings (SMTP for magic links)
  • Application settings
  • Admin account
```

Follow the prompts to configure:
1. **Database** - MySQL/MariaDB connection details
2. **Email** - SMTP settings for magic link logins
3. **Admin Account** - Your administrator login
4. **Student Account** - Optional student account
5. **Sample Data** - 500+ practice questions

## Persistent Data

All data is stored in Docker volumes and survives restarts:

| Volume | Purpose |
|--------|---------|
| `y6-practice-exam-config` | Configuration files |
| `y6-practice-exam-data` | Uploads and app data |
| `y6-practice-exam-logs` | Application logs |
| `y6-practice-exam-db` | MySQL database |
| `y6-practice-exam-redis` | Redis cache |

## Commands

### Start/Stop

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f app
```

### Management

```bash
# Re-run setup wizard
docker exec -it y6-practice-exam setup

# Update from GitHub
docker exec -it y6-practice-exam update

# Run migrations
docker exec -it y6-practice-exam migrate

# Seed Y6 Cambridge curriculum questions
docker exec -it y6-practice-exam seed

# Show available commands
docker exec -it y6-practice-exam help

# Open shell
docker exec -it y6-practice-exam shell
```

### Question Import/Export

The system includes Y6 Cambridge curriculum questions that can be imported/exported:

```bash
# Export all questions to JSON and CSV files
docker exec -it y6-practice-exam export
# Files saved to: data/questions/

# Import questions from bundled curriculum data
docker exec -it y6-practice-exam import

# Import specific subject only (ENG, MAT, ICT, SCI)
docker exec -it y6-practice-exam import data/questions MAT

# Clear existing questions before import
docker exec -it y6-practice-exam import data/questions "" --clear
```

**Bundled Question Sets:**
- English: 450 questions in 10 sets
- Mathematics: 447 questions in 10 sets
- ICT: 442 questions in 10 sets
- Science: 433 questions in 10 sets

Total: **1,772 Y6 Cambridge curriculum questions**

### Update to Latest Version

```bash
# Pull latest image
docker pull ranaislek/y6-practice-exam:latest

# Restart with new image
docker-compose down
docker-compose up -d
```

## Environment Variables

You can override settings via environment variables in `docker-compose.yml`:

```yaml
environment:
  # Database
  - DB_HOST=db
  - DB_PORT=3306
  - DB_NAME=y6_practice_exam
  - DB_USER=y6user
  - DB_PASSWORD=yourpassword

  # Email
  - SMTP_ENABLED=true
  - SMTP_HOST=smtp.gmail.com
  - SMTP_PORT=587
  - SMTP_USER=your@email.com
  - SMTP_PASSWORD=yourapppassword

  # App
  - SECRET_KEY=your-secret-key
  - APP_ENV=production
  - AUTO_UPDATE=true
```

## Auto-Updates from GitHub

If enabled during setup, the app will automatically pull updates from GitHub on each restart:

1. Commits pushed to GitHub
2. Restart container: `docker-compose restart app`
3. App pulls latest changes and restarts

To update manually:
```bash
docker exec -it y6-practice-exam update
```

## Backup & Restore

### Backup

```bash
# Backup all volumes
docker run --rm \
  -v y6-practice-exam-config:/config \
  -v y6-practice-exam-data:/data \
  -v y6-practice-exam-db:/db \
  -v $(pwd):/backup \
  alpine tar czf /backup/y6-backup-$(date +%Y%m%d).tar.gz /config /data /db
```

### Restore

```bash
# Stop containers first
docker-compose down

# Restore from backup
docker run --rm \
  -v y6-practice-exam-config:/config \
  -v y6-practice-exam-data:/data \
  -v y6-practice-exam-db:/db \
  -v $(pwd):/backup \
  alpine tar xzf /backup/y6-backup-20240101.tar.gz -C /

# Start again
docker-compose up -d
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs y6-practice-exam

# Check health
docker inspect y6-practice-exam | grep -A 10 Health
```

### Database connection failed

```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection manually
docker exec -it y6-practice-exam-db mysql -u root -p
```

### Reset setup

```bash
# Remove setup flag to re-run wizard
docker exec -it y6-practice-exam rm /app/config/.setup_complete

# Restart
docker-compose restart app
```

### Clear all data (CAUTION!)

```bash
# Stop everything
docker-compose down

# Remove volumes
docker volume rm y6-practice-exam-config y6-practice-exam-data y6-practice-exam-db

# Start fresh
docker-compose up -d
```

## Building Locally

```bash
# Build image
docker build -t y6-practice-exam:local .

# Run local build
docker run -it -p 5001:5001 \
  -v y6_config:/app/config \
  -v y6_data:/app/data \
  y6-practice-exam:local
```

## Publishing to Docker Hub

```bash
# Login
docker login

# Build and tag
docker build -t ranaislek/y6-practice-exam:latest .
docker tag ranaislek/y6-practice-exam:latest ranaislek/y6-practice-exam:v1.0.0

# Push
docker push ranaislek/y6-practice-exam:latest
docker push ranaislek/y6-practice-exam:v1.0.0
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     App      │  │    MySQL     │  │    Redis     │  │
│  │   (Flask)    │──│   Database   │  │   (Cache)    │  │
│  │   :5001      │  │   :3306      │  │   :6379      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │          │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐  │
│  │ config vol   │  │   db vol     │  │  redis vol   │  │
│  │ data vol     │  │              │  │              │  │
│  │ logs vol     │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/y6-practice-exam/issues
- Email: support@springgate.edu.my
