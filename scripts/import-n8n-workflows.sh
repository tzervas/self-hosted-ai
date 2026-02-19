#!/usr/bin/env bash
set -euo pipefail

# Import n8n workflows from config/n8n-workflows/ directory via REST API
# Usage: ./scripts/import-n8n-workflows.sh [N8N_URL] [API_KEY]
#
# Environment variables (alternative to args):
#   N8N_URL     - n8n base URL (default: http://n8n.automation:5678)
#   N8N_API_KEY - n8n API key

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOWS_DIR="${SCRIPT_DIR}/../config/n8n-workflows"

N8N_URL="${1:-${N8N_URL:-http://n8n.automation:5678}}"
API_KEY="${2:-${N8N_API_KEY:-}}"

if [[ -z "$API_KEY" ]]; then
    echo "Error: n8n API key required."
    echo "Usage: $0 [URL] API_KEY"
    echo "   or: N8N_API_KEY=x $0"
    echo ""
    echo "Generate an API key in n8n: Settings > API > Create API Key"
    exit 1
fi

echo "==> Importing n8n workflows"
echo "    URL: ${N8N_URL}"
echo "    Workflows dir: ${WORKFLOWS_DIR}"

# Wait for n8n to be healthy
echo "==> Waiting for n8n to be healthy..."
for i in $(seq 1 30); do
    if curl -sf "${N8N_URL}/healthz" > /dev/null 2>&1; then
        echo "    n8n is healthy!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "Error: n8n not healthy after 5 minutes"
        exit 1
    fi
    echo "    Waiting... (attempt $i/30)"
    sleep 10
done

# Get existing workflows
echo "==> Checking existing workflows..."
EXISTING=$(curl -sf "${N8N_URL}/api/v1/workflows" \
    -H "X-N8N-API-KEY: ${API_KEY}" \
    | python3 -c "import sys,json; [print(w['name']) for w in json.load(sys.stdin).get('data',[])]" 2>/dev/null) || true

IMPORTED=0
SKIPPED=0
FAILED=0

for workflow_file in "${WORKFLOWS_DIR}"/*.json; do
    [[ -f "$workflow_file" ]] || continue

    filename=$(basename "$workflow_file")
    workflow_name=$(python3 -c "
import json
with open('${workflow_file}') as f:
    data = json.load(f)
print(data.get('name', '${filename}'))
" 2>/dev/null || echo "${filename}")

    # Skip if already exists
    if echo "${EXISTING}" | grep -qF "${workflow_name}" 2>/dev/null; then
        echo "    Skipped (exists): ${workflow_name}"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo "==> Importing: ${workflow_name}"

    # Remove id field if present (n8n auto-generates)
    PAYLOAD=$(python3 -c "
import json
with open('${workflow_file}') as f:
    data = json.load(f)
data.pop('id', None)
print(json.dumps(data))
" 2>/dev/null)

    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
        "${N8N_URL}/api/v1/workflows" \
        -H "X-N8N-API-KEY: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" 2>/dev/null) || HTTP_CODE="000"

    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "201" ]]; then
        echo "    Imported: ${workflow_name}"
        IMPORTED=$((IMPORTED + 1))
    else
        echo "    Warning: Failed to import ${workflow_name} (HTTP ${HTTP_CODE})"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "==> Import complete!"
echo "    Imported: ${IMPORTED}"
echo "    Skipped:  ${SKIPPED}"
echo "    Failed:   ${FAILED}"
echo ""
echo "NOTE: Workflows are imported as inactive. Activate them in the n8n UI."

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
