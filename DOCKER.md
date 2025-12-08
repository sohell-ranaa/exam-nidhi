# Y6 Practice Exam - Docker Deployment Guide

## Quick Start (External MySQL)

This guide assumes MySQL/MariaDB is already installed on your server.

### Step 1: Pull the Docker Image

```bash
docker pull sohellbd/y6-practice-exam:latest
```

### Step 2: Create Deployment Directory

```bash
mkdir -p /opt/y6-exam && cd /opt/y6-exam
```

### Step 3: Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    image: sohellbd/y6-practice-exam:latest
    container_name: y6-practice-exam
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - y6-config:/app/config
      - y6-data:/app/data
      - y6-logs:/app/logs
    environment:
      - APP_ENV=production
      - TZ=Asia/Kuala_Lumpur
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  y6-config:
  y6-data:
  y6-logs:
EOF
```

### Step 4: Prepare MySQL Database

On your MySQL server, create the database and user:

```sql
-- Login to MySQL
mysql -u root -p

-- Create database
CREATE DATABASE y6_practice_exam CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (replace 'yourpassword' with a strong password)
CREATE USER 'y6user'@'%' IDENTIFIED BY 'yourpassword';
GRANT ALL PRIVILEGES ON y6_practice_exam.* TO 'y6user'@'%';
FLUSH PRIVILEGES;

-- Exit
EXIT;
```

### Step 5: Start the Application

```bash
docker compose up -d
```

### Step 6: First-Time Setup

The setup wizard runs automatically on first start. View it with:

```bash
docker compose logs -f app
```

Or run setup manually:

```bash
docker exec -it y6-practice-exam setup
```

**Setup Wizard will ask for:**

1. **Database Connection:**
   - Host: `host.docker.internal` (or your server's IP)
   - Port: `3306`
   - Database: `y6_practice_exam`
   - User: `y6user`
   - Password: `yourpassword`

2. **SMTP Settings** (for email magic links)

3. **Admin Account** (email & password)

4. **Import Sample Questions** (Y6 Cambridge curriculum - 1,772 questions)

### Step 7: Access the Application

Open browser: `http://YOUR_SERVER_IP:5001`

---

## Setup Caddy (SSL & Reverse Proxy)

Caddy automatically handles SSL certificates from Let's Encrypt.

### Option A: Caddy via Docker (Recommended)

Update your docker-compose.yml:

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  caddy:
    image: caddy:2-alpine
    container_name: y6-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config

  app:
    image: sohellbd/y6-practice-exam:latest
    container_name: y6-practice-exam
    restart: unless-stopped
    expose:
      - "5001"
    volumes:
      - y6-config:/app/config
      - y6-data:/app/data
      - y6-logs:/app/logs
    environment:
      - APP_ENV=production
      - TZ=Asia/Kuala_Lumpur
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  y6-config:
  y6-data:
  y6-logs:
  caddy-data:
  caddy-config:
EOF
```

Create Caddyfile:

```bash
cat > Caddyfile << 'EOF'
exam.yourschool.edu {
    reverse_proxy app:5001 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
EOF
```

Restart:

```bash
docker compose down
docker compose up -d
```

### Option B: Install Caddy on Host

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y

# Create Caddyfile
sudo tee /etc/caddy/Caddyfile << 'EOF'
exam.yourschool.edu {
    reverse_proxy 127.0.0.1:5001 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
EOF

# Restart Caddy
sudo systemctl restart caddy
```

---

## Management Commands

```bash
# View logs
docker compose logs -f app

# Re-run setup wizard
docker exec -it y6-practice-exam setup

# Import Y6 Cambridge curriculum questions
docker exec -it y6-practice-exam import

# Export questions to JSON/CSV
docker exec -it y6-practice-exam export

# Run database migrations
docker exec -it y6-practice-exam migrate

# Open shell inside container
docker exec -it y6-practice-exam shell

# Show all available commands
docker exec -it y6-practice-exam help
```

---

## Question Import/Export

### Bundled Questions (Y6 Cambridge Curriculum)
- English: 450 questions
- Mathematics: 447 questions
- ICT: 442 questions
- Science: 433 questions
- **Total: 1,772 questions**

### Import Questions

```bash
# Import all bundled questions
docker exec -it y6-practice-exam import

# Import specific subject (ENG, MAT, ICT, SCI)
docker exec -it y6-practice-exam import data/questions MAT

# Clear existing and reimport
docker exec -it y6-practice-exam import data/questions "" --clear
```

### Export Questions

```bash
docker exec -it y6-practice-exam export
# Files saved to: /app/data/questions/
```

### Custom Questions JSON Format

See `data/questions/SAMPLE_TEMPLATE.json` for format:

```json
{
  "subject": {
    "code": "ENG",
    "name": "English",
    "color": "#0078D4"
  },
  "question_sets": [
    {
      "title": "Grammar Test Unit 1",
      "duration_minutes": 60,
      "questions": [
        {
          "question_number": 1,
          "question_type": "mcq",
          "question_text": "Choose the correct answer...",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "B",
          "marks": 1
        }
      ]
    }
  ]
}
```

---

## Update to Latest Version

```bash
cd /opt/y6-exam

# Pull latest image
docker compose pull

# Restart with new image
docker compose down
docker compose up -d
```

---

## Backup & Restore

### Backup

```bash
# Backup Docker volumes
docker run --rm \
  -v y6-config:/config \
  -v y6-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/y6-backup-$(date +%Y%m%d).tar.gz /config /data

# Backup MySQL database
mysqldump -u y6user -p y6_practice_exam > y6_db_backup_$(date +%Y%m%d).sql
```

### Restore

```bash
# Restore Docker volumes
docker compose down
docker run --rm \
  -v y6-config:/config \
  -v y6-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/y6-backup-20240101.tar.gz -C /

# Restore MySQL database
mysql -u y6user -p y6_practice_exam < y6_db_backup_20240101.sql

docker compose up -d
```

---

## Troubleshooting

### Container won't start

```bash
docker compose logs app
```

### Database connection failed

- Ensure MySQL is running: `sudo systemctl status mysql`
- Check if user can connect: `mysql -u y6user -p -h 127.0.0.1 y6_practice_exam`
- For Docker, use `host.docker.internal` as database host

### Reset setup

```bash
docker exec -it y6-practice-exam rm /app/config/.setup_complete
docker compose restart app
```

### IP shows as 127.0.0.1

Ensure Caddy is configured with proper headers:
```
header_up X-Real-IP {remote_host}
header_up X-Forwarded-For {remote_host}
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f app` |
| Update | `docker compose pull && docker compose up -d` |
| Setup | `docker exec -it y6-practice-exam setup` |
| Import Questions | `docker exec -it y6-practice-exam import` |
| Export Questions | `docker exec -it y6-practice-exam export` |
| Shell | `docker exec -it y6-practice-exam shell` |
| Help | `docker exec -it y6-practice-exam help` |

---

## Build from Source

```bash
cd /path/to/y6-practice-exam

# Build image
docker build --network=host -t sohellbd/y6-practice-exam:v1.0.0 .
docker tag sohellbd/y6-practice-exam:v1.0.0 sohellbd/y6-practice-exam:latest

# Push to Docker Hub
docker login -u sohellbd
docker push sohellbd/y6-practice-exam:v1.0.0
docker push sohellbd/y6-practice-exam:latest
```

---

## Support

- GitHub: https://github.com/sohellbd/y6-practice-exam
- Email: support@springgate.edu.my
