#!/usr/bin/env bash
# Upload Open WebUI tools via API
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_DIR="$PROJECT_ROOT/config/openwebui-tools"

# Configuration
OPENWEBUI_URL="${OPENWEBUI_URL:-https://ai.vectorweight.com}"
OPENWEBUI_API_KEY="${OPENWEBUI_API_KEY:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[⚠]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

# Check prerequisites
if [ -z "$OPENWEBUI_API_KEY" ]; then
    error "OPENWEBUI_API_KEY environment variable not set"
    echo ""
    echo "To get your API key:"
    echo "  1. Go to $OPENWEBUI_URL"
    echo "  2. Settings → Account → API Keys"
    echo "  3. Create new key or copy existing"
    echo "  4. Export: export OPENWEBUI_API_KEY='your-key-here'"
    echo ""
    exit 1
fi

# Tools to upload (all tools in config/openwebui-tools/)
TOOLS=(
    # Core generative tools
    "image_generation.py"
    "video_generation.py"
    "text_to_speech.py"
    "music_generator_pro.py"

    # Editing and processing tools
    "image_upscaler.py"
    "background_remover.py"
    "video_editor.py"
    "audio_processor.py"

    # Utility and integration tools
    "searxng_search.py"
    "web_fetch.py"
    "memory_store.py"
    "n8n_workflow_runner.py"
)

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Open WebUI Tools Upload                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
log "Target: $OPENWEBUI_URL"
log "Tools directory: $TOOLS_DIR"
echo ""

# Upload each tool
UPLOADED=0
FAILED=0

for tool_file in "${TOOLS[@]}"; do
    tool_path="$TOOLS_DIR/$tool_file"

    if [ ! -f "$tool_path" ]; then
        error "Tool not found: $tool_file"
        ((FAILED++))
        continue
    fi

    log "Uploading $tool_file..."

    # Read tool content
    tool_content=$(cat "$tool_path")

    # Upload via API (Open WebUI tools API endpoint)
    # Note: Endpoint may vary by Open WebUI version
    # This is the typical pattern - adjust if needed
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$OPENWEBUI_URL/api/v1/tools/import" \
        -H "Authorization: Bearer $OPENWEBUI_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"content\": $(jq -Rs . <<< "$tool_content")}" \
        2>&1 || echo "000")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        success "Uploaded: $tool_file"
        ((UPLOADED++))
    else
        error "Failed to upload $tool_file (HTTP $http_code)"
        [ -n "$body" ] && echo "  Response: $body"
        ((FAILED++))
    fi
done

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Upload Summary                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
success "Uploaded: $UPLOADED tools"
[ $FAILED -gt 0 ] && error "Failed: $FAILED tools"
echo ""

if [ $UPLOADED -gt 0 ]; then
    echo "Next steps:"
    echo "  1. Go to $OPENWEBUI_URL → Settings → Tools"
    echo "  2. Verify tools are listed"
    echo "  3. Test: Ask AI to 'Create an image of a sunset'"
    echo ""
fi

exit $FAILED
