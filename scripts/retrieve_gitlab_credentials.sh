#!/bin/bash
# GitLab Credential Retrieval Script
# Run this directly on the homelab server (192.168.1.170)

set -e

echo "========================================="
echo "GitLab Credential Retrieval"
echo "========================================="
echo ""

# Check if running as root or with docker permissions
if ! docker ps &>/dev/null; then
    echo "Error: Cannot access Docker. Please run with sudo or ensure user is in docker group."
    exit 1
fi

# Get GitLab URL
GITLAB_URL=$(docker inspect gitlab | grep -oP '(?<="EXTERNAL_URL=")[^"]*' || echo "http://192.168.1.170")
echo "GitLab URL: $GITLAB_URL"
echo ""

# Method 1: Reset root password
echo "========================================="
echo "METHOD 1: Reset Root Password"
echo "========================================="
echo ""
echo "Run the following command to reset root password:"
echo ""
echo "docker exec -it gitlab gitlab-rake 'gitlab:password:reset[root]'"
echo ""
echo "This will prompt you to enter a new password for the root user."
echo ""

# Method 2: Retrieve OAuth Applications
echo "========================================="
echo "METHOD 2: Retrieve OAuth Applications"
echo "========================================="
echo ""
echo "Attempting to retrieve OAuth applications..."
echo ""

OAUTH_CMD="Doorkeeper::Application.all.each { |a| puts \"\\n=== #{a.name} ===\"; puts \"Client ID: #{a.uid}\"; puts \"Client Secret: #{a.secret}\"; puts \"Redirect URI: #{a.redirect_uri}\"; puts \"Scopes: #{a.scopes}\" }"

docker exec gitlab gitlab-rails runner "$OAUTH_CMD" 2>&1 || {
    echo "Failed to retrieve OAuth apps automatically."
    echo ""
    echo "Run this command manually:"
    echo "docker exec -it gitlab gitlab-rails console"
    echo ""
    echo "Then in the console, run:"
    echo "Doorkeeper::Application.all.each { |a| puts \"\\n=== \#{a.name} ===\"; puts \"Client ID: \#{a.uid}\"; puts \"Client Secret: \#{a.secret}\"; puts \"Redirect URI: \#{a.redirect_uri}\"; puts \"Scopes: \#{a.scopes}\" }"
}

echo ""
echo "========================================="
echo "METHOD 3: Create Personal Access Token"
echo "========================================="
echo ""
echo "Once logged in as root, you can create a Personal Access Token:"
echo "1. Go to: $GITLAB_URL/-/profile/personal_access_tokens"
echo "2. Create token with 'api' scope"
echo "3. Save the token immediately (it won't be shown again)"
echo ""

echo "========================================="
echo "GitLab Access Information"
echo "========================================="
echo "Web Interface: $GITLAB_URL"
echo "Username: root"
echo "SSH Port: 2224"
echo "Registry: $GITLAB_URL:5050"
echo ""
echo "To access via web:"
echo "1. Open: $GITLAB_URL"
echo "2. Login as 'root'"
echo "3. Use password you set or reset"
echo ""
