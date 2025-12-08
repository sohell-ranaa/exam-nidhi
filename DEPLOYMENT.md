# Y6 Practice Exam - Complete Deployment Guide

## Overview

This guide covers everything from building the Docker image to deploying on a new server.

---

## Part 1: Build and Push Docker Image

### Prerequisites (Build Machine)
- Docker installed
- Docker Hub account (or other registry)

### Step 1: Build the Docker Image

```bash
cd /home/rana-workspace/y6-practice-exam

# Build with version tag
docker build -t ranaislek/y6-practice-exam:v1.0.0 .

# Also tag as latest
docker tag ranaislek/y6-practice-exam:v1.0.0 ranaislek/y6-practice-exam:latest
```

### Step 2: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push both tags
docker push ranaislek/y6-practice-exam:v1.0.0
docker push ranaislek/y6-practice-exam:latest
```

Or use the build script:
```bash
./docker/build-and-push.sh v1.0.0
```

---

## Part 2: Deploy to New Server

### Prerequisites (Target Server)
- Ubuntu 20.04+ or similar Linux
- Docker and Docker Compose installed
- Domain name (optional, for SSL)

### Step 1: Install Docker (if not installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Logout and login again for group changes
```

### Step 2: Create Deployment Directory

```bash
mkdir -p /opt/y6-practice-exam
cd /opt/y6-practice-exam
```

### Step 3: Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    image: ranaislek/y6-practice-exam:latest
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
    depends_on:
      - db
    networks:
      - y6-network

  db:
    image: mariadb:10.11
    container_name: y6-practice-exam-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=y6rootpass2024
      - MYSQL_DATABASE=y6_practice_exam
      - MYSQL_USER=y6user
      - MYSQL_PASSWORD=y6pass2024
    volumes:
      - y6-db:/var/lib/mysql
    networks:
      - y6-network

volumes:
  y6-config:
  y6-data:
  y6-logs:
  y6-db:

networks:
  y6-network:
    driver: bridge
EOF
```

### Step 4: Start the Application

```bash
# Pull latest image
docker-compose pull

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### Step 5: Run Setup Wizard

On first run, the setup wizard starts automatically. Access logs to see the wizard:

```bash
docker-compose logs -f app
```

Or run setup manually:
```bash
docker exec -it y6-practice-exam setup
```

The wizard will prompt for:
1. **Database Connection** - Use these values:
   - Host: `db`
   - Port: `3306`
   - Database: `y6_practice_exam`
   - User: `y6user`
   - Password: `y6pass2024`

2. **SMTP Settings** (for email magic links)
   - Host: Your SMTP server (e.g., `smtp.gmail.com`)
   - Port: `587`
   - Username: Your email
   - Password: Your app password

3. **Admin Account**
   - Email: `admin@yourschool.edu`
   - Password: Your secure password

4. **Sample Data** - Choose to import Y6 Cambridge curriculum questions

### Step 6: Access the Application

Open in browser: `http://YOUR_SERVER_IP:5001`

---

## Part 3: Caddy Reverse Proxy (Recommended)

Caddy automatically handles SSL certificates and is much simpler than Nginx.

### Option A: Caddy via Docker (Recommended)

Update your `docker-compose.yml` to include Caddy:

```yaml
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
    networks:
      - y6-network

  app:
    image: ranaislek/y6-practice-exam:latest
    container_name: y6-practice-exam
    restart: unless-stopped
    # Remove port mapping - Caddy handles external access
    # ports:
    #   - "5001:5001"
    expose:
      - "5001"
    volumes:
      - y6-config:/app/config
      - y6-data:/app/data
      - y6-logs:/app/logs
    environment:
      - APP_ENV=production
      - TZ=Asia/Kuala_Lumpur
    depends_on:
      - db
    networks:
      - y6-network

  db:
    image: mariadb:10.11
    container_name: y6-practice-exam-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=y6rootpass2024
      - MYSQL_DATABASE=y6_practice_exam
      - MYSQL_USER=y6user
      - MYSQL_PASSWORD=y6pass2024
    volumes:
      - y6-db:/var/lib/mysql
    networks:
      - y6-network

volumes:
  y6-config:
  y6-data:
  y6-logs:
  y6-db:
  caddy-data:
  caddy-config:

networks:
  y6-network:
    driver: bridge
```

### Create Caddyfile

```bash
cat > Caddyfile << 'EOF'
exam.yourschool.edu {
    # Automatic HTTPS with Let's Encrypt

    # Forward real client IP
    reverse_proxy app:5001 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
EOF
```

That's it! Caddy automatically:
- Obtains SSL certificate from Let's Encrypt
- Redirects HTTP to HTTPS
- Forwards the real client IP

### Option B: Install Caddy on Host

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y

# Create Caddyfile
sudo nano /etc/caddy/Caddyfile
```

```
exam.yourschool.edu {
    reverse_proxy 127.0.0.1:5001 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

```bash
# Restart Caddy
sudo systemctl restart caddy
```

---

## Part 4: Import Questions

### Using Bundled Y6 Cambridge Curriculum

The Docker image includes 1,772 Y6 Cambridge curriculum questions. To import:

```bash
docker exec -it y6-practice-exam import
```

### Import Custom Questions

1. **Create JSON file** following the template in `data/questions/SAMPLE_TEMPLATE.json`

2. **Copy to container:**
```bash
docker cp your_questions.json y6-practice-exam:/app/data/questions/
```

3. **Import:**
```bash
# Import all subjects
docker exec -it y6-practice-exam import

# Import specific subject only
docker exec -it y6-practice-exam import data/questions ENG

# Clear existing and reimport
docker exec -it y6-practice-exam import data/questions "" --clear
```

### JSON File Format

```json
{
  "subject": {
    "code": "ENG",           // ENG, MAT, ICT, SCI
    "name": "English",
    "color": "#0078D4"
  },
  "question_sets": [
    {
      "title": "Grammar Test Unit 1",
      "description": "Basic grammar assessment",
      "duration_minutes": 60,
      "questions": [
        {
          "question_number": 1,
          "question_type": "mcq",       // mcq, written, fill_blank, matching, labeling, drawing
          "question_text": "Choose the correct answer...",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_answer": "B",        // A, B, C, D for MCQ
          "marks": 1,
          "hint": "Optional hint",
          "explanation": "Optional explanation"
        }
      ]
    }
  ]
}
```

### Question Types

| Type | Fields Required |
|------|----------------|
| `mcq` | `options` (array), `correct_answer` (A/B/C/D) |
| `written` | `correct_answer` (text for grading reference) |
| `fill_blank` | `correct_answer` (expected text) |
| `matching` | `matching_pairs` ([{left, right}, ...]) |
| `labeling` | `labels` ([{id, text, x, y}, ...]), `image_url` |
| `drawing` | `drawing_template` ({width, height, background}) |

---

## Part 5: Maintenance

### View Logs

```bash
# All logs
docker-compose logs -f

# App logs only
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app
```

### Update to Latest Version

```bash
cd /opt/y6-practice-exam

# Pull latest image
docker-compose pull

# Restart with new image
docker-compose down
docker-compose up -d
```

### Backup Data

```bash
# Backup all volumes
docker run --rm \
  -v y6-config:/config \
  -v y6-data:/data \
  -v y6-db:/db \
  -v $(pwd):/backup \
  alpine tar czf /backup/y6-backup-$(date +%Y%m%d).tar.gz /config /data /db

# Export questions to JSON
docker exec -it y6-practice-exam export
docker cp y6-practice-exam:/app/data/questions ./backup/
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore volumes
docker run --rm \
  -v y6-config:/config \
  -v y6-data:/data \
  -v y6-db:/db \
  -v $(pwd):/backup \
  alpine tar xzf /backup/y6-backup-20240101.tar.gz -C /

# Start services
docker-compose up -d
```

### Reset Setup

```bash
# Re-run setup wizard
docker exec -it y6-practice-exam rm /app/config/.setup_complete
docker-compose restart app
```

### Available Commands

```bash
docker exec -it y6-practice-exam help

# Commands:
#   serve   - Start the application
#   setup   - Run setup wizard
#   migrate - Run database migrations
#   seed    - Import Y6 curriculum questions
#   import  - Import questions from JSON/CSV
#   export  - Export questions to JSON/CSV
#   update  - Pull updates from GitHub
#   shell   - Open bash shell
```

---

## Part 6: Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs app

# Check health
docker inspect y6-practice-exam | grep -A 10 Health
```

### Database Connection Failed

```bash
# Check if database is running
docker-compose ps db

# Test connection
docker exec -it y6-practice-exam-db mysql -u y6user -py6pass2024 y6_practice_exam
```

### IP Address Shows as 127.0.0.1

Ensure Nginx is configured with proper headers:
```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

### Clear Everything and Start Fresh

```bash
docker-compose down
docker volume rm y6-config y6-data y6-logs y6-db
docker-compose up -d
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start | `docker-compose up -d` |
| Stop | `docker-compose down` |
| Restart | `docker-compose restart` |
| Logs | `docker-compose logs -f app` |
| Update | `docker-compose pull && docker-compose up -d` |
| Setup | `docker exec -it y6-practice-exam setup` |
| Import Questions | `docker exec -it y6-practice-exam import` |
| Export Questions | `docker exec -it y6-practice-exam export` |
| Shell | `docker exec -it y6-practice-exam shell` |

---

## Support

- GitHub Issues: https://github.com/yourusername/y6-practice-exam/issues
- Email: support@springgate.edu.my
