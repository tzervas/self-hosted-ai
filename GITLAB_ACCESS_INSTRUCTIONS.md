# GitLab Access and OAuth Credentials Guide

## Current Status
- **GitLab URL**: http://192.168.1.170 (or https://192.168.1.170)
- **Username**: `root`
- **SSH Port**: 2224
- **Registry Port**: 5050
- **Container Name**: `gitlab`
- **Server**: homelab (192.168.1.170)

## Issue Detected
The Docker exec command on the homelab server is experiencing connectivity issues with containerd socket, preventing automated credential retrieval.

## Solution 1: Fix Docker Exec (Recommended)

SSH into the homelab server and run:

```bash
ssh homelab
sudo systemctl restart docker
# Wait a few seconds for containers to restart
docker ps  # Verify gitlab is running
```

Then try:
```bash
docker exec gitlab gitlab-rails runner "puts Doorkeeper::Application.all.map { |a| {name: a.name, uid: a.uid, secret: a.secret, redirect_uri: a.redirect_uri} }.to_yaml"
```

## Solution 2: Reset Root Password & Access Web UI

### Reset Password
```bash
ssh homelab
docker exec -it gitlab gitlab-rake 'gitlab:password:reset[root]'
# Follow the prompts to set a new password
```

### Access Web Interface
1. Open browser: http://192.168.1.170
2. Login as `root` with your new password
3. Navigate to Admin Area → Applications
4. View or create OAuth applications

## Solution 3: Retrieve OAuth Applications via Rails Console

If docker exec works:

```bash
ssh homelab
docker exec -it gitlab gitlab-rails console
```

Then in the Rails console:
```ruby
# List all OAuth applications
Doorkeeper::Application.all.each do |app|
  puts "\n=== #{app.name} ==="
  puts "Application ID: #{app.id}"
  puts "Client ID (UID): #{app.uid}"
  puts "Client Secret: #{app.secret}"
  puts "Redirect URI: #{app.redirect_uri}"
  puts "Scopes: #{app.scopes}"
  puts "Confidential: #{app.confidential}"
  puts "Created: #{app.created_at}"
end
```

## Solution 4: Create New OAuth Application via Web UI

1. Login to GitLab: http://192.168.1.170
2. Go to: **Admin Area** (wrench icon) → **Applications**
3. Click **New Application**
4. Fill in:
   - **Name**: Your application name (e.g., "Keycloak", "Open WebUI")
   - **Redirect URI**: Your callback URL (e.g., `https://keycloak.vectorweight.com/auth/realms/master/broker/gitlab/endpoint`)
   - **Confidential**: Check this box
   - **Scopes**: Select `api`, `read_user`, `read_api`, `openid`, `profile`, `email`
5. Click **Save application**
6. **IMPORTANT**: Copy the Application ID and Secret immediately (secret won't be shown again)

## Solution 5: Create Personal Access Token

For API access without OAuth:

1. Login to GitLab: http://192.168.1.170
2. Go to: **User Settings** (avatar) → **Access Tokens**
3. Create token with:
   - **Name**: API Access
   - **Scopes**: `api`, `read_user`, `write_repository`
   - **Expiration**: Set as needed
4. Click **Create personal access token**
5. **IMPORTANT**: Copy the token immediately

## Verify GitLab is Accessible

```bash
# Test from homelab server
ssh homelab "curl -I http://localhost:80"

# Test from local machine
curl -I http://192.168.1.170
```

## Retrieve OAuth App Credentials (Alternative Method)

If you can access GitLab's PostgreSQL database:

```bash
ssh homelab
docker exec gitlab gitlab-psql -d gitlabhq_production -c "SELECT name, uid, secret, redirect_uri FROM oauth_applications;"
```

## Common OAuth Application Names

Depending on your setup, you might be looking for:
- `keycloak` - Keycloak integration
- `open-webui` - Open WebUI integration
- `argocd` - ArgoCD SSO
- `n8n` - n8n automation

## Next Steps After Getting Credentials

1. **For Keycloak OAuth**:
   - Add GitLab as an Identity Provider
   - Use Client ID and Secret in Keycloak configuration

2. **For Open WebUI**:
   - Configure OAuth in Open WebUI settings
   - Set OAuth provider to GitLab
   - Add Client ID and Secret

3. **For API Keys**:
   - Use Personal Access Tokens
   - Store securely (environment variables or secrets manager)
   - Rotate regularly

## Troubleshooting

### Cannot Access GitLab Web Interface
```bash
# Check if container is running
ssh homelab "docker ps | grep gitlab"

# Check GitLab logs
ssh homelab "docker logs gitlab --tail 100"

# Restart GitLab
ssh homelab "docker restart gitlab"
```

### Docker Exec Not Working
```bash
# Restart Docker daemon
ssh homelab "sudo systemctl restart docker"

# Alternative: Access container filesystem directly
ssh homelab "sudo ls /var/lib/docker/volumes/gitlab_config/_data/"
```

### Need to Change GitLab URL
Edit GitLab configuration:
```bash
ssh homelab
docker exec gitlab vim /etc/gitlab/gitlab.rb
# Change external_url
docker restart gitlab
```

## Security Notes

- Store OAuth secrets securely (use sealed-secrets in Kubernetes)
- Rotate credentials regularly
- Use HTTPS in production (configure Traefik/cert-manager)
- Enable 2FA for root account
- Create separate admin users instead of using root

## Helper Script

A credential retrieval script has been created at:
```
/home/kang/Documents/projects/github/self-hosted-ai/scripts/retrieve_gitlab_credentials.sh
```

Once Docker exec is fixed, run it with:
```bash
scp scripts/retrieve_gitlab_credentials.sh homelab:/tmp/
ssh homelab "bash /tmp/retrieve_gitlab_credentials.sh"
```
