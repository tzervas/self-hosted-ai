# MCP Servers Helm Chart

Deploys Model Context Protocol (MCP) servers for AI agent tool integration.

## Overview

This chart deploys:
- **MCPO Proxy**: HTTP bridge for stdio-based MCP servers
- **Bundled MCP Servers**: Core tooling for development workflows

## MCP Servers Included

### Context & Memory
| Server | Purpose | API Key Required |
|--------|---------|------------------|
| `mcp-server-memory` | Persistent context/memory store | No |
| `mcp-server-time` | Time/date operations | No |
| `mcp-server-sequential-thinking` | Multi-step reasoning | No |

### Development Tools
| Server | Purpose | API Key Required |
|--------|---------|------------------|
| `mcp-server-filesystem` | File operations | No |
| `mcp-server-git` | Git operations | No |
| `mcp-server-fetch` | Web content fetching | No |
| `mcp-server-puppeteer` | Browser automation | No |

### Search (No API Keys)
| Server | Purpose | API Key Required |
|--------|---------|------------------|
| `mcp-server-duckduckgo` | DuckDuckGo search | No |
| `searxng` (via Open WebUI) | Privacy-focused meta-search | No |

### Service Integration
| Server | Purpose | Configuration |
|--------|---------|---------------|
| `mcp-server-gitlab` | GitLab API integration | Uses self-hosted instance |
| `mcp-server-postgres` | Database operations | Internal PostgreSQL |
| `mcp-server-kubernetes` | K8s operations (read-only) | ServiceAccount |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Open WebUI / Agents                          │
│                    (MCP Client via HTTP)                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCPO Proxy                                │
│                    (stdio → HTTP bridge)                         │
│                      Port 8000                                   │
└───────┬─────────┬─────────┬─────────┬─────────┬────────────────┘
        │         │         │         │         │
        ▼         ▼         ▼         ▼         ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │filesys │ │  git   │ │ fetch  │ │ memory │ │ gitlab │
   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
      stdio      stdio      stdio      stdio      stdio
```

## Installation

```bash
# Via ArgoCD (recommended)
argocd app sync mcp-servers

# Manual Helm
helm upgrade --install mcp-servers ./helm/mcp-servers -n self-hosted-ai
```

## Configuration

### values.yaml

```yaml
# Enable/disable specific servers
servers:
  filesystem:
    enabled: true
    # Mounted paths available to the server
    paths:
      - /workspace
      - /tmp
    
  git:
    enabled: true
    # Default repository path
    repoPath: /workspace
    
  fetch:
    enabled: true
    # User agent for requests
    userAgent: "MCP-Fetch/1.0"
    
  memory:
    enabled: true
    # Persistence for memory
    persistence:
      enabled: true
      size: 1Gi
    
  gitlab:
    enabled: true
    # Uses internal GitLab instance
    url: "https://git.vectorweight.com"
    # Token from secret
    tokenSecret:
      name: gitlab-mcp-token
      key: token
      
  kubernetes:
    enabled: true
    # Read-only operations only
    readOnly: true
    # Allowed namespaces
    namespaces:
      - self-hosted-ai
      - monitoring
      
  duckduckgo:
    enabled: true
    # Search result limit
    maxResults: 10
    
  time:
    enabled: true
    timezone: "America/New_York"
    
  sequentialThinking:
    enabled: true
    # Max reasoning steps
    maxSteps: 10

# MCPO Proxy configuration
mcpoProxy:
  image: ghcr.io/open-webui/mcpo:latest
  port: 8000
  replicas: 1
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

## Open WebUI Integration

Add MCP servers to Open WebUI via Tools settings:

```
URL: http://mcp-servers:8000
Name: Development Tools
```

Or via API:
```bash
curl -X POST https://ai.vectorweight.com/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Development Tools",
    "url": "http://mcp-servers:8000",
    "type": "mcp"
  }'
```

## n8n Integration

Use the MCP Client Tool node in n8n:

1. Add "MCP Client Tool" node
2. Configure endpoint: `http://mcp-servers:8000`
3. Select available tools from discovery

## Security Considerations

- **filesystem**: Limited to specified paths only
- **kubernetes**: Read-only by default, scoped to namespaces
- **gitlab**: Uses dedicated service account token
- **No external API keys**: All servers work without third-party services

## Troubleshooting

### Check server status
```bash
kubectl logs -n self-hosted-ai deployment/mcp-servers

# List available tools
curl http://mcp-servers.self-hosted-ai:8000/tools
```

### Test specific server
```bash
# Test filesystem
curl -X POST http://mcp-servers.self-hosted-ai:8000/execute \
  -d '{"tool": "filesystem_read", "arguments": {"path": "/workspace/README.md"}}'
```

## References

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [MCPO Proxy](https://github.com/open-webui/mcpo)
- [MCP Server Registry](https://registry.modelcontextprotocol.io)
