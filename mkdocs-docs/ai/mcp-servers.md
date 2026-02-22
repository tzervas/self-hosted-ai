---
title: MCP Servers
description: Model Context Protocol tool servers for AI agents
---

# MCP Servers

## Overview

AI agents access tools via Model Context Protocol (MCP) servers, deployed in the `self-hosted-ai` namespace.

**Endpoint**: `http://mcp-servers.self-hosted-ai:8000/mcp`

## Available Servers

| Server | Purpose | Auth |
|--------|---------|------|
| filesystem | Read/write workspace files | RBAC-scoped |
| git | Repository operations | ServiceAccount |
| fetch | HTTP requests | None |
| memory | Knowledge graph storage | Persistent volume |
| duckduckgo | Web search | None |
| sequential-thinking | Reasoning chains | None |
| gitlab | GitLab API operations | K8s secret token |
| postgres | Database queries | Cluster PostgreSQL |
| kubernetes | Read-only K8s access | ServiceAccount |

## Configuration

**Helm chart**: `helm/mcp-servers/values.yaml`

Each MCP server is configured as a container in the deployment, with the MCPO proxy providing a unified HTTP endpoint.

## Usage

MCP tools are accessible from:

- **Open WebUI**: Via tool configuration
- **n8n**: Via HTTP request nodes
- **Claude Code**: Via `.claude/.mcp.json` configuration
- **Direct API**: Via MCPO proxy endpoint

## Adding a New MCP Server

1. Add server configuration to `helm/mcp-servers/values.yaml`
2. Update the MCPO proxy configuration
3. Commit and let ArgoCD sync
4. Test via the MCPO endpoint
