#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONFIG_FILE="${CONFIG_DIR}/app.env"
SETUP_DONE_FLAG="${CONFIG_DIR}/.setup_complete"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           Y6 Practice Exam System                         ║"
echo "║           Spring Gate Private School                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if setup is needed
check_setup_needed() {
    if [ ! -f "$SETUP_DONE_FLAG" ] || [ ! -f "$CONFIG_FILE" ]; then
        return 0  # Setup needed
    fi
    return 1  # Setup complete
}

# Function to load config
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${GREEN}Loading configuration...${NC}"
        set -a
        source "$CONFIG_FILE"
        set +a
    fi
}

# Function to check for updates from GitHub
check_updates() {
    if [ -n "$GITHUB_REPO" ] && [ "$AUTO_UPDATE" = "true" ]; then
        echo -e "${YELLOW}Checking for updates from GitHub...${NC}"

        # Store current commit
        CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

        # Fetch updates
        if git fetch origin main 2>/dev/null; then
            REMOTE_COMMIT=$(git rev-parse origin/main 2>/dev/null || echo "unknown")

            if [ "$CURRENT_COMMIT" != "$REMOTE_COMMIT" ] && [ "$REMOTE_COMMIT" != "unknown" ]; then
                echo -e "${YELLOW}Updates available! Pulling changes...${NC}"
                git pull origin main 2>/dev/null || echo -e "${RED}Failed to pull updates${NC}"
                echo -e "${GREEN}Updates applied successfully!${NC}"
            else
                echo -e "${GREEN}Already up to date.${NC}"
            fi
        else
            echo -e "${YELLOW}Could not check for updates (no git remote configured)${NC}"
        fi
    fi
}

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}Waiting for database connection...${NC}"

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if python3 -c "
import sys
sys.path.insert(0, '/app')
from dbs.connection import get_connection
try:
    conn = get_connection()
    conn.close()
    exit(0)
except Exception as e:
    print(f'Connection error: {e}', file=sys.stderr)
    exit(1)
"; then
            echo -e "${GREEN}Database connected!${NC}"
            return 0
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -e "${YELLOW}Waiting for database... (attempt $RETRY_COUNT/$MAX_RETRIES)${NC}"
        sleep 2
    done

    echo -e "${RED}Could not connect to database after $MAX_RETRIES attempts${NC}"
    return 1
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    cd /app

    # Run schema creation
    if [ -f "dbs/migrations/001_initial_schema.sql" ]; then
        python3 -c "
from dbs.connection import get_connection
import os

conn = get_connection()
cursor = conn.cursor()

# Check if tables exist
cursor.execute(\"SHOW TABLES LIKE 'users'\")
if not cursor.fetchone():
    print('Creating database schema...')
    # Read and execute migration
    migration_dir = 'dbs/migrations'
    for filename in sorted(os.listdir(migration_dir)):
        if filename.endswith('.sql'):
            filepath = os.path.join(migration_dir, filename)
            print(f'Running {filename}...')
            with open(filepath, 'r') as f:
                sql = f.read()
                for statement in sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            cursor.execute(statement)
                        except Exception as e:
                            print(f'Warning: {e}')
    conn.commit()
    print('Schema created successfully!')
else:
    print('Database schema already exists.')

cursor.close()
conn.close()
" 2>/dev/null || echo -e "${YELLOW}Migration check completed${NC}"
    fi

    echo -e "${GREEN}Migrations complete!${NC}"
}

# Function to seed initial data
seed_data() {
    if [ "$SEED_DATA" = "true" ] && [ ! -f "${CONFIG_DIR}/.seeded" ]; then
        echo -e "${YELLOW}Seeding Y6 Cambridge curriculum questions...${NC}"

        cd /app
        # First try to import from bundled JSON files (Y6 Cambridge curriculum)
        if [ -d "data/questions" ] && [ -f "data/questions/manifest.json" ]; then
            echo -e "${BLUE}Importing from bundled curriculum data...${NC}"
            python3 tools/import_questions.py 2>/dev/null || echo -e "${YELLOW}Import skipped or already done${NC}"
            touch "${CONFIG_DIR}/.seeded"
        elif [ -f "seeds/seed_all_questions.py" ]; then
            # Fallback to seed script
            python3 seeds/seed_all_questions.py 2>/dev/null || echo -e "${YELLOW}Seeding skipped or already done${NC}"
            touch "${CONFIG_DIR}/.seeded"
        fi

        echo -e "${GREEN}Seeding complete!${NC}"
    fi
}

# Function to import questions from JSON/CSV
import_questions() {
    echo -e "${YELLOW}Importing questions...${NC}"
    cd /app

    IMPORT_DIR="${2:-data/questions}"
    SUBJECT_FILTER="${3:-}"

    if [ -n "$SUBJECT_FILTER" ]; then
        python3 tools/import_questions.py --dir "$IMPORT_DIR" --subject "$SUBJECT_FILTER" $4
    else
        python3 tools/import_questions.py --dir "$IMPORT_DIR" $4
    fi

    echo -e "${GREEN}Import complete!${NC}"
}

# Function to export questions to JSON/CSV
export_questions() {
    echo -e "${YELLOW}Exporting questions...${NC}"
    cd /app

    python3 tools/export_questions.py --csv

    echo -e "${GREEN}Export complete!${NC}"
    echo -e "${BLUE}Files saved to: data/questions/${NC}"
}

# Function to start the application
start_app() {
    echo -e "${GREEN}Starting Y6 Practice Exam System...${NC}"
    echo -e "${BLUE}Server running at http://0.0.0.0:5001${NC}"
    echo ""

    cd /app

    if [ "$APP_ENV" = "production" ]; then
        # Production mode with gunicorn
        exec gunicorn --bind 0.0.0.0:5001 \
            --workers ${WORKERS:-2} \
            --threads ${THREADS:-4} \
            --timeout 120 \
            --access-logfile - \
            --error-logfile - \
            --capture-output \
            "app:app"
    else
        # Development mode
        exec python3 app.py
    fi
}

# Main logic
case "${1:-serve}" in
    setup)
        # Force run setup wizard
        python3 /app/docker/setup-wizard.py
        ;;

    serve)
        # Check if first-time setup is needed
        if check_setup_needed; then
            echo -e "${YELLOW}First-time setup required!${NC}"

            # Check if running interactively (has TTY)
            if [ -t 0 ]; then
                # Interactive mode - run setup wizard
                python3 /app/docker/setup-wizard.py

                if [ $? -ne 0 ]; then
                    echo -e "${RED}Setup failed or was cancelled.${NC}"
                    exit 1
                fi
            else
                # Non-interactive mode - wait for manual setup
                echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
                echo -e "${YELLOW}  Container started but setup is required.${NC}"
                echo -e "${YELLOW}  Run the setup wizard manually:${NC}"
                echo ""
                echo -e "${GREEN}    docker exec -it y6-practice-exam setup${NC}"
                echo ""
                echo -e "${YELLOW}  Waiting for setup to complete...${NC}"
                echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"

                # Wait for setup to complete (check every 5 seconds)
                while check_setup_needed; do
                    sleep 5
                done

                echo -e "${GREEN}Setup complete! Starting application...${NC}"
            fi
        fi

        # Load configuration
        load_config

        # Check for updates
        check_updates

        # Wait for database
        wait_for_db || exit 1

        # Run migrations
        run_migrations

        # Seed data if enabled
        seed_data

        # Start the app
        start_app
        ;;

    migrate)
        load_config
        wait_for_db || exit 1
        run_migrations
        ;;

    seed)
        load_config
        wait_for_db || exit 1
        SEED_DATA=true
        rm -f "${CONFIG_DIR}/.seeded"
        seed_data
        ;;

    import)
        # Import questions: docker exec app import [dir] [subject] [--clear]
        load_config
        wait_for_db || exit 1
        import_questions "$@"
        ;;

    export)
        # Export questions to JSON/CSV
        load_config
        wait_for_db || exit 1
        export_questions
        ;;

    update)
        echo -e "${YELLOW}Forcing update from GitHub...${NC}"
        load_config
        AUTO_UPDATE=true
        check_updates
        ;;

    shell)
        exec /bin/bash
        ;;

    help)
        echo -e "${BLUE}Available commands:${NC}"
        echo ""
        echo "  serve     - Start the application (default)"
        echo "  setup     - Run the setup wizard"
        echo "  migrate   - Run database migrations"
        echo "  seed      - Seed Y6 Cambridge curriculum questions"
        echo "  import    - Import questions from JSON/CSV files"
        echo "              Usage: import [dir] [subject] [--clear]"
        echo "  export    - Export questions to JSON/CSV files"
        echo "  update    - Pull updates from GitHub"
        echo "  shell     - Open a bash shell"
        echo "  help      - Show this help message"
        echo ""
        ;;

    *)
        exec "$@"
        ;;
esac
