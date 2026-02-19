#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Open WebUI tools from config/openwebui-tools/ directory
# Usage: ./scripts/bootstrap-openwebui-tools.sh [OPENWEBUI_URL] [EMAIL] [PASSWORD]
#
# Environment variables (alternative to args):
#   OPENWEBUI_URL      - Open WebUI base URL (default: http://open-webui.ai-services:8080)
#   OPENWEBUI_EMAIL    - Admin email
#   OPENWEBUI_PASSWORD - Admin password

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="${SCRIPT_DIR}/../config/openwebui-tools"

OPENWEBUI_URL="${1:-${OPENWEBUI_URL:-http://open-webui.ai-services:8080}}"
EMAIL="${2:-${OPENWEBUI_EMAIL:-}}"
PASSWORD="${3:-${OPENWEBUI_PASSWORD:-}}"

if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
    echo "Error: Admin email and password required."
    echo "Usage: $0 [URL] EMAIL PASSWORD"
    echo "   or: OPENWEBUI_EMAIL=x OPENWEBUI_PASSWORD=y $0"
    exit 1
fi

echo "==> Bootstrapping Open WebUI tools"
echo "    URL: ${OPENWEBUI_URL}"
echo "    Tools dir: ${TOOLS_DIR}"

# Wait for Open WebUI to be healthy
echo "==> Waiting for Open WebUI to be healthy..."
for i in $(seq 1 30); do
    if curl -sf "${OPENWEBUI_URL}/health" > /dev/null 2>&1; then
        echo "    Open WebUI is healthy!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "Error: Open WebUI not healthy after 5 minutes"
        exit 1
    fi
    echo "    Waiting... (attempt $i/30)"
    sleep 10
done

# Authenticate
echo "==> Authenticating..."
TOKEN=$(curl -sf "${OPENWEBUI_URL}/api/v1/auths/signin" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null) || {
    echo "Error: Authentication failed. Check credentials."
    exit 1
}
echo "    Authenticated successfully."

# Get existing tools
echo "==> Checking existing tools..."
EXISTING_TOOLS=$(curl -sf "${OPENWEBUI_URL}/api/v1/tools/" \
    -H "Authorization: Bearer ${TOKEN}" \
    | python3 -c "import sys,json; [print(t['id']) for t in json.load(sys.stdin)]" 2>/dev/null) || true

# Load each tool from the tools directory
LOADED=0
UPDATED=0
FAILED=0

for tool_file in "${TOOLS_DIR}"/*.py; do
    [[ -f "$tool_file" ]] || continue

    filename=$(basename "$tool_file" .py)
    tool_id="${filename}"

    # Read tool metadata from docstring
    tool_name=$(python3 -c "
import re
with open('${tool_file}') as f:
    content = f.read()
m = re.search(r'title:\s*(.+)', content)
print(m.group(1).strip() if m else '${filename}')
" 2>/dev/null || echo "${filename}")

    tool_desc=$(python3 -c "
import re
with open('${tool_file}') as f:
    content = f.read()
m = re.search(r'description:\s*(.+)', content)
print(m.group(1).strip() if m else '')
" 2>/dev/null || echo "")

    # Read the Python source
    tool_content=$(python3 -c "
import json, sys
with open('${tool_file}') as f:
    print(json.dumps(f.read()))
" 2>/dev/null)

    echo "==> Processing: ${tool_name} (${tool_id})"

    # Build JSON payload
    PAYLOAD=$(python3 -c "
import json
print(json.dumps({
    'id': '${tool_id}',
    'name': '${tool_name}',
    'content': json.loads(${tool_content}),
    'meta': {'description': '${tool_desc}'},
    'is_active': True,
    'is_global': True
}))
")

    # Check if tool exists
    if echo "${EXISTING_TOOLS}" | grep -qx "${tool_id}" 2>/dev/null; then
        # Update existing tool
        HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
            "${OPENWEBUI_URL}/api/v1/tools/id/${tool_id}/update" \
            -H "Authorization: Bearer ${TOKEN}" \
            -H "Content-Type: application/json" \
            -d "${PAYLOAD}" 2>/dev/null) || HTTP_CODE="000"

        if [[ "$HTTP_CODE" == "200" ]]; then
            echo "    Updated: ${tool_name}"
            UPDATED=$((UPDATED + 1))
        else
            echo "    Warning: Failed to update ${tool_name} (HTTP ${HTTP_CODE})"
            FAILED=$((FAILED + 1))
        fi
    else
        # Create new tool
        HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
            "${OPENWEBUI_URL}/api/v1/tools/create" \
            -H "Authorization: Bearer ${TOKEN}" \
            -H "Content-Type: application/json" \
            -d "${PAYLOAD}" 2>/dev/null) || HTTP_CODE="000"

        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "201" ]]; then
            echo "    Created: ${tool_name}"
            LOADED=$((LOADED + 1))
        else
            echo "    Warning: Failed to create ${tool_name} (HTTP ${HTTP_CODE})"
            FAILED=$((FAILED + 1))
        fi
    fi
done

echo ""
echo "==> Bootstrap complete!"
echo "    Created: ${LOADED}"
echo "    Updated: ${UPDATED}"
echo "    Failed:  ${FAILED}"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
