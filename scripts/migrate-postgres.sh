#!/usr/bin/env bash
#
# PostgreSQL 16 → 17 Migration Script
# Zero-downtime parallel deployment strategy
#

set -euo pipefail

# Configuration
POSTGRES_16_HOST="${POSTGRES_16_HOST:-localhost}"
POSTGRES_16_PORT="${POSTGRES_16_PORT:-5432}"
POSTGRES_17_HOST="${POSTGRES_17_HOST:-localhost}"
POSTGRES_17_PORT="${POSTGRES_17_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-litellm}"
POSTGRES_USER="${POSTGRES_USER:-litellm}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?ERROR: POSTGRES_PASSWORD not set}"

BACKUP_DIR="${DATA_PATH:-/data}/postgres-migration"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if both PostgreSQL instances are running
    if ! docker ps | grep -q "postgres-db"; then
        log_error "PostgreSQL 16 (postgres-db) is not running"
        exit 1
    fi
    
    if ! docker ps | grep -q "postgres-17-db"; then
        log_error "PostgreSQL 17 (postgres-17-db) is not running"
        log_info "Start it with: docker compose -f docker-compose.yml -f docker-compose.multimodal.yml --profile postgres-migration up -d postgres-17"
        exit 1
    fi
    
    # Check connectivity
    if ! docker exec postgres-db pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_error "Cannot connect to PostgreSQL 16"
        exit 1
    fi
    
    if ! docker exec postgres-17-db pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        log_error "Cannot connect to PostgreSQL 17"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

create_backup() {
    log_info "Creating backup of PostgreSQL 16..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Full database dump
    docker exec postgres-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        > "$BACKUP_DIR/pg16_backup_${TIMESTAMP}.sql"
    
    # Also dump globals (roles, etc.)
    docker exec postgres-db pg_dumpall -U "$POSTGRES_USER" --globals-only \
        > "$BACKUP_DIR/pg16_globals_${TIMESTAMP}.sql"
    
    log_success "Backup created: $BACKUP_DIR/pg16_backup_${TIMESTAMP}.sql"
}

migrate_data() {
    log_info "Migrating data from PostgreSQL 16 to 17..."
    
    # Import globals first
    log_info "Importing global objects (roles, tablespaces)..."
    docker exec -i postgres-17-db psql -U "$POSTGRES_USER" -d postgres \
        < "$BACKUP_DIR/pg16_globals_${TIMESTAMP}.sql" || true
    
    # Drop and recreate database to ensure clean slate
    log_info "Recreating database on PostgreSQL 17..."
    docker exec postgres-17-db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
    docker exec postgres-17-db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"
    
    # Import data
    log_info "Importing database dump..."
    docker exec -i postgres-17-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        < "$BACKUP_DIR/pg16_backup_${TIMESTAMP}.sql"
    
    log_success "Data migration complete"
}

verify_migration() {
    log_info "Verifying migration..."
    
    # Get row counts from PG16
    log_info "Checking PostgreSQL 16 statistics..."
    local pg16_tables
    pg16_tables=$(docker exec postgres-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
    
    # Get row counts from PG17
    log_info "Checking PostgreSQL 17 statistics..."
    local pg17_tables
    pg17_tables=$(docker exec postgres-17-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
    
    log_info "PostgreSQL 16 tables: $pg16_tables"
    log_info "PostgreSQL 17 tables: $pg17_tables"
    
    if [ "$pg16_tables" -eq "$pg17_tables" ]; then
        log_success "Table counts match"
    else
        log_warning "Table counts don't match - manual verification recommended"
    fi
    
    # Test basic queries
    log_info "Testing basic queries on PostgreSQL 17..."
    docker exec postgres-17-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();"
    
    log_success "Verification complete"
}

update_litellm_config() {
    log_warning "MANUAL STEP REQUIRED: Update LiteLLM configuration"
    echo ""
    echo "To switch LiteLLM to PostgreSQL 17, update docker-compose.multimodal.yml:"
    echo ""
    echo "  litellm:"
    echo "    environment:"
    echo "      - DATABASE_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@postgres-17:5432/litellm"
    echo "    depends_on:"
    echo "      - postgres-17"
    echo ""
    echo "Then restart LiteLLM:"
    echo "  docker compose -f docker-compose.yml -f docker-compose.multimodal.yml restart litellm"
    echo ""
}

cleanup_old_postgres() {
    log_warning "MANUAL STEP: Remove PostgreSQL 16 after verification"
    echo ""
    echo "After verifying PostgreSQL 17 works correctly for at least 24 hours:"
    echo ""
    echo "1. Stop PostgreSQL 16:"
    echo "   docker compose -f docker-compose.yml -f docker-compose.multimodal.yml stop postgres"
    echo ""
    echo "2. Remove the service from docker-compose.multimodal.yml"
    echo ""
    echo "3. Optionally backup and remove old data:"
    echo "   tar -czf postgres-16-final-backup.tar.gz ${DATA_PATH:-/data}/postgres"
    echo "   rm -rf ${DATA_PATH:-/data}/postgres"
    echo ""
}

main() {
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  PostgreSQL 16 → 17 Migration (Parallel Deployment)      ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "Migration strategy: Zero-downtime parallel deployment"
    log_info "Timestamp: $TIMESTAMP"
    echo ""
    
    # Confirmation
    read -rp "Start migration? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Migration cancelled"
        exit 0
    fi
    
    echo ""
    log_info "=== Phase 1: Prerequisites ==="
    check_prerequisites
    
    echo ""
    log_info "=== Phase 2: Backup ==="
    create_backup
    
    echo ""
    log_info "=== Phase 3: Data Migration ==="
    migrate_data
    
    echo ""
    log_info "=== Phase 4: Verification ==="
    verify_migration
    
    echo ""
    log_info "=== Phase 5: Configuration Update ==="
    update_litellm_config
    
    echo ""
    log_info "=== Phase 6: Cleanup (Manual) ==="
    cleanup_old_postgres
    
    echo ""
    log_success "Migration preparation complete!"
    echo ""
    log_info "Next steps:"
    echo "1. Verify PostgreSQL 17 is working correctly"
    echo "2. Update LiteLLM configuration to use PostgreSQL 17"
    echo "3. Test all LiteLLM functionality"
    echo "4. After 24h verification period, remove PostgreSQL 16"
    echo ""
    log_info "Backup location: $BACKUP_DIR/pg16_backup_${TIMESTAMP}.sql"
}

main "$@"
