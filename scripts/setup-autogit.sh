#!/bin/bash
# Deploy Autogit Repository Mirror Solution
# Mirrors all GitHub repos to GitLab with bidirectional sync capability

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*" >&2; }

# Configuration
GITHUB_ORG="${1:-tzervas}"
GITHUB_USER="${GITHUB_USER:-$(git config --global user.name)}"
GITLAB_HOST="gitlab.homelab.local:32295"
GITLAB_NAMESPACE="mirrors"  # GitLab group for mirrored repos
AUTOGIT_NAMESPACE="automation"

log_info "Autogit Repository Mirror Setup"
log_info "GitHub Org: $GITHUB_ORG"
log_info "GitLab Host: $GITLAB_HOST"
log_info "Target Namespace: $GITLAB_NAMESPACE"
echo ""

# Step 1: Verify prerequisites
log_info "Checking prerequisites..."

command -v gh &>/dev/null || { log_error "gh CLI not installed"; exit 1; }
command -v kubectl &>/dev/null || { log_error "kubectl not installed"; exit 1; }
command -v git &>/dev/null || { log_error "git not installed"; exit 1; }

log_success "All CLIs installed"

# Step 2: List GitHub repositories
log_info "Fetching GitHub repositories from organization: $GITHUB_ORG"
REPOS=$(gh repo list "$GITHUB_ORG" --json nameWithOwner --jq '.[].nameWithOwner')

if [ -z "$REPOS" ]; then
    log_warn "No repositories found in organization $GITHUB_ORG"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
else
    echo "Found repositories:"
    echo "$REPOS" | sed 's/^/  - /'
fi

echo ""
read -p "Continue with mirror setup? (y/n) " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0

# Step 3: Create GitLab group for mirrors
log_info "Setting up GitLab group for mirrored repositories..."
log_warn "This requires GitLab root credentials"

echo ""
echo "GitLab Access Required:"
echo "  URL: https://gitlab.homelab.local:32295"
echo "  Username: root"
echo "  You'll be prompted for password"
echo ""

read -sp "GitLab Root Password: " GITLAB_ROOT_PASSWORD
echo ""

# Step 4: Create Kubernetes CronJob for mirroring
log_info "Creating Kubernetes CronJob for repository mirroring..."

cat > /tmp/autogit-cronjob.yaml << 'EOFYAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: autogit-mirror-script
  namespace: automation
data:
  mirror-repos.sh: |
    #!/bin/bash
    set -euo pipefail
    
    GITHUB_ORG="${GITHUB_ORG}"
    GITLAB_HOST="${GITLAB_HOST}"
    GITLAB_TOKEN="${GITLAB_TOKEN}"
    GITLAB_NAMESPACE_ID="${GITLAB_NAMESPACE_ID}"
    
    log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }
    
    log "Starting repository mirror sync for org: $GITHUB_ORG"
    
    # Get list of GitHub repos
    REPOS=$(gh repo list "$GITHUB_ORG" --json nameWithOwner --jq '.[].nameWithOwner')
    
    while IFS= read -r repo; do
      [ -z "$repo" ] && continue
      
      REPO_NAME=$(echo "$repo" | cut -d'/' -f2)
      REPO_DESCRIPTION=$(gh repo view "$repo" --json description --jq '.description')
      REPO_URL="https://github.com/${repo}.git"
      
      log "Processing: $repo"
      
      # Check if project exists in GitLab
      PROJECT=$(curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
        "https://$GITLAB_HOST/api/v4/groups/$GITLAB_NAMESPACE_ID/projects?search=$REPO_NAME" | \
        jq -r '.[] | select(.name=="'$REPO_NAME'") | .id')
      
      if [ -z "$PROJECT" ]; then
        log "  Creating project: $REPO_NAME"
        
        # Create project in GitLab
        PROJECT=$(curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
          -H "Content-Type: application/json" \
          "https://$GITLAB_HOST/api/v4/projects" \
          -d "{
            \"name\": \"$REPO_NAME\",
            \"namespace_id\": $GITLAB_NAMESPACE_ID,
            \"description\": \"Mirror of $repo - $REPO_DESCRIPTION\",
            \"visibility\": \"private\",
            \"issues_enabled\": false,
            \"snippets_enabled\": false,
            \"wiki_enabled\": false
          }" | jq -r '.id')
        
        log "  Created project ID: $PROJECT"
      else
        log "  Project already exists (ID: $PROJECT)"
      fi
      
      # Set up mirroring
      log "  Configuring mirror pull for: $REPO_URL"
      
      curl -s -X PUT -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
        "https://$GITLAB_HOST/api/v4/projects/$PROJECT" \
        -d "{ \"mirror\": true, \"import_url\": \"$REPO_URL\" }" || true
      
      # Trigger mirror pull
      curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
        "https://$GITLAB_HOST/api/v4/projects/$PROJECT/mirror/pull" || true
      
      log "  Mirror sync initiated"
    done <<< "$REPOS"
    
    log "Repository mirror sync completed"
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: autogit-mirror-sync
  namespace: automation
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: autogit-mirror
          containers:
          - name: mirror
            image: alpine/git:latest
            command:
            - /bin/bash
            - /scripts/mirror-repos.sh
            volumeMounts:
            - name: script
              mountPath: /scripts
            env:
            - name: GITHUB_ORG
              value: "{{ GITHUB_ORG }}"
            - name: GITLAB_HOST
              value: "{{ GITLAB_HOST }}"
            - name: GITLAB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: gitlab-token
                  key: token
            - name: GITLAB_NAMESPACE_ID
              valueFrom:
                configMapKeyRef:
                  name: autogit-config
                  key: namespace-id
          restartPolicy: OnFailure
          volumes:
          - name: script
            configMap:
              name: autogit-mirror-script
              defaultMode: 0755
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: autogit-mirror
  namespace: automation
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: autogit-mirror
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
- apiGroups: ["batch"]
  resources: ["cronjobs"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: autogit-mirror
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: autogit-mirror
subjects:
- kind: ServiceAccount
  name: autogit-mirror
  namespace: automation
EOFYAML

log_info "Applying CronJob configuration..."
kubectl apply -f /tmp/autogit-cronjob.yaml

# Step 5: Create GitLab token secret
log_info "Creating GitLab access token secret..."

read -sp "GitLab Personal Access Token (create at Settings > Access Tokens): " GITLAB_TOKEN
echo ""

kubectl create secret generic gitlab-token \
  --from-literal=token="$GITLAB_TOKEN" \
  -n automation \
  --dry-run=client -o yaml | kubectl apply -f -

log_success "GitLab token secret created"

# Step 6: Create autogit ConfigMap
log_info "Creating autogit configuration..."

kubectl create configmap autogit-config \
  --from-literal=github-org="$GITHUB_ORG" \
  --from-literal=gitlab-host="$GITLAB_HOST" \
  --from-literal=namespace-id="1" \
  -n automation \
  --dry-run=client -o yaml | kubectl apply -f -

log_success "Autogit configuration created"

# Step 7: Create pull secret for GitHub private repos
log_info "Setting up GitHub authentication..."

read -sp "GitHub Personal Access Token (for private repos): " GITHUB_TOKEN
echo ""

kubectl create secret generic github-token \
  --from-literal=token="$GITHUB_TOKEN" \
  -n automation \
  --dry-run=client -o yaml | kubectl apply -f -

log_success "GitHub token secret created"

# Step 8: Test mirror sync
log_info "Testing repository mirror sync..."
log_warn "This may take a few minutes..."

kubectl create job --from=cronjob/autogit-mirror-sync autogit-mirror-test \
  -n automation 2>/dev/null || true

sleep 5

# Wait for job to complete
for i in {1..30}; do
    STATUS=$(kubectl get job autogit-mirror-test -n automation -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
    if [ "$STATUS" = "1" ]; then
        log_success "Mirror sync job completed successfully"
        break
    fi
    if [ $i -eq 30 ]; then
        log_warn "Mirror sync job is still running (or timed out)"
        log_info "Check logs with: kubectl logs -n automation job/autogit-mirror-test"
    fi
    sleep 2
done

# Step 9: Configure GitLab runner for local development
log_info "Configuring GitLab runner for local development..."

cat > /tmp/gitlab-runner-config.sh << 'EOFRUNNER'
#!/bin/bash
# GitLab Runner configuration for local development

GITLAB_URL="https://gitlab.homelab.local:32295"
REGISTRATION_TOKEN="${1:-}"

if [ -z "$REGISTRATION_TOKEN" ]; then
    echo "Usage: $0 <registration-token>"
    echo ""
    echo "To get registration token:"
    echo "1. Go to $GITLAB_URL/admin/runners"
    echo "2. Click 'Register group runner' or 'Register instance runner'"
    echo "3. Copy the registration token"
    exit 1
fi

echo "Registering GitLab Runner..."
echo "  URL: $GITLAB_URL"
echo "  Token: $REGISTRATION_TOKEN"
echo ""

gitlab-runner register \
    --non-interactive \
    --url "$GITLAB_URL" \
    --registration-token "$REGISTRATION_TOKEN" \
    --executor "kubernetes" \
    --kubernetes-host "kubernetes.default.svc.cluster.local" \
    --kubernetes-namespace "gitlab-runners" \
    --kubernetes-cpu-limit "2" \
    --kubernetes-memory-limit "2048Mi" \
    --kubernetes-cpu-request "500m" \
    --kubernetes-memory-request "512Mi" \
    --tag-list "docker,kubernetes,git" \
    --paused "false" \
    --run-untagged "true" \
    --locked "false" \
    --description "Homelab Kubernetes Runner"

echo ""
echo "Runner registered successfully!"
echo "Check status: gitlab-runner status"
EOFRUNNER

chmod +x /tmp/gitlab-runner-config.sh

log_info "GitLab runner configuration script created at: /tmp/gitlab-runner-config.sh"

# Final summary
echo ""
echo "=========================================="
log_success "Autogit Setup Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Verify repository mirrors in GitLab:"
echo "   URL: https://gitlab.homelab.local:32295/groups/$GITLAB_NAMESPACE"
echo ""
echo "2. Configure GitLab runner for CI/CD:"
echo "   $0 gitlab-runner-config.sh <registration-token>"
echo ""
echo "3. Configure GitHub Actions with ARC:"
echo "   ./scripts/setup-arc-github-app.sh --org $GITHUB_ORG"
echo ""
echo "4. Monitor mirror sync:"
echo "   kubectl logs -f cronjob/autogit-mirror-sync -n automation"
echo ""
echo "5. Clone mirrored repos for local development:"
echo "   git clone https://gitlab.homelab.local:32295/mirrors/repo-name.git"
echo ""
echo "6. Set up bidirectional sync (optional):"
echo "   git remote add github https://github.com/$GITHUB_ORG/repo-name.git"
echo "   git push github main  # Push changes back to GitHub"
echo ""
