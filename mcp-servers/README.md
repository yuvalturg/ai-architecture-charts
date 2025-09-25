# MCP Servers Helm Chart

This Helm chart deploys MCP (Model Context Protocol) servers using the Toolhive operator that provides external tools and capabilities to AI models. MCP servers enable AI agents to interact with external systems, APIs, and services.

## Architecture Overview

The mcp-servers chart creates:
- **Toolhive Operator**: Centralized operator for managing MCP servers
- **MCPServer Custom Resources**: Kubernetes-native MCP server definitions
- **Automated Proxy Management**: Toolhive handles networking and communication
- **Secure Credential Management**: Integration with Kubernetes secrets
- **Support for Multiple MCP Types**: Weather services, Oracle SQLcl, and extensible architecture

### Key Components

1. **Toolhive Operator**: Manages the lifecycle of MCP servers
2. **MCPServer CRDs**: Define MCP server specifications declaratively
3. **Oracle SQLcl MCP**: Database interaction capabilities using Oracle's SQLcl
4. **Weather MCP**: External weather API integration
5. **Secure Secret Management**: Credentials sourced from Kubernetes secrets

### ToolHive-Only Deployment Architecture

This chart exclusively uses ToolHive MCPServer custom resources for all MCP server deployments, providing a unified, operator-managed approach:

#### ToolHive-Managed Servers (All servers via MCPServer CRDs)
- **Oracle SQLcl MCP**: Uses `transport: stdio`
  - Deployed as MCPServer CRD managed by Toolhive operator
  - SQLcl's native MCP mode communicates via stdio
  - Toolhive automatically proxies stdio to HTTP/SSE for web access
  - Accessible at: `http://mcp-oracle-sqlcl-proxy:8080/sse`

- **Weather MCP**: Uses `transport: sse`
  - Deployed as MCPServer CRD managed by Toolhive operator
  - Native SSE transport with Toolhive proxy management
  - Consistent networking and service discovery
  - Accessible at: `http://mcp-mcp-weather-proxy:8000/sse`

**Benefits of ToolHive-Only Approach:**
- Unified deployment model for all MCP servers
- Consistent service naming and networking
- Automatic proxy and service account management
- Simplified configuration and maintenance
## Included Files

| File | Description |
|------|-------------|
| `helm/` | Helm chart for MCP servers deployment |
| `oracle-sqlcl/` | Oracle SQLcl MCP container source |
| `weather/` | Weather MCP container source code |
| `README.md` | This documentation |

## Prerequisites

- OpenShift cluster (4.12+)
- Helm 3.x
- Access to container registries
- Network connectivity to external APIs
- Oracle database (for Oracle SQLcl MCP server)

## Installation

### Dependency Hierarchy & Installation Sequence

The MCP servers deployment has the following dependency hierarchy that must be followed for proper installation:

```
1. Toolhive CRDs & Infrastructure Prerequisites
   ├── OpenShift cluster (4.12+)
   ├── Helm 3.x
   ├── Container registry access
   └── Toolhive CRDs installation (REQUIRED FIRST)

2. External Dependencies (if using Oracle SQLcl MCP)
   └── Oracle Database
       ├── Database instance running
       ├── Sales schema/user created
       └── Kubernetes secret with credentials

3. Toolhive Operator
   ├── Operator deployment
   └── RBAC permissions

4. MCP Servers
   ├── Weather MCP (requires Tavily API key)
   └── Oracle SQLcl MCP (requires Oracle DB + secret)
```

### Installation Sequence

**Step 1: Install Toolhive CRDs and Verify Prerequisites**
```bash
# Verify OpenShift cluster access
oc whoami
oc get nodes

# Verify Helm installation
helm version

# Add Toolhive Helm repository
helm repo add toolhive https://stacklok.github.io/toolhive
helm repo update

# Install Toolhive CRDs (REQUIRED FIRST for MCP servers)
helm install toolhive-crds toolhive/toolhive-operator-crds --version 0.0.30
```

**Step 2: Deploy External Dependencies (Oracle SQLcl MCP only)**
```bash
# Deploy Oracle database using the Oracle 23ai chart (using 23.5.0.0 for platform compatibility)
helm install oracle-db ../oracle23ai/helm --namespace <your-namespace> --set oracle.image.tag=23.5.0.0

# Wait for Oracle database StatefulSet to be ready
oc wait --for=jsonpath='{.status.readyReplicas}'=1 statefulset/oracle23ai --timeout=600s

# Verify Oracle secret was created by the database chart
oc get secret oracle23ai
```

**Step 3: Install Toolhive Operator**
```bash
# Install Toolhive operator with 1Gi memory (default 128Mi is insufficient)
helm install toolhive-operator toolhive/toolhive-operator --version 0.2.19 --namespace <your-namespace> --set operator.resources.requests.memory=1Gi --set operator.resources.limits.memory=1Gi

# Verify Toolhive operator is running
oc get pods -l app.kubernetes.io/name=toolhive-operator --namespace <your-namespace>
```

**Step 4: Install MCP Servers**
```bash
# Install MCP servers (operator already installed in Step 3)
# PVC and SCC permissions will be created automatically by the helm chart
helm install mcp-servers ./helm --namespace <your-namespace>

# Verify MCP servers are running
oc get pods -l toolhive=true --namespace <your-namespace>
oc get mcpservers --namespace <your-namespace>
```

### Quick Start

```bash
# Install everything in one command (includes ToolHive CRDs, operator, and MCP servers)
helm install mcp-servers ./helm --namespace <your-namespace> --create-namespace

# Check deployment status
kubectl get mcpservers -n <your-namespace>
kubectl get pods -l app.kubernetes.io/name=toolhive-operator -n <your-namespace>
kubectl get pods -l toolhive=true -n <your-namespace>
```

**What gets deployed:**
- ✅ ToolHive CRDs (MCPServer custom resources)
- ✅ ToolHive operator (manages MCP server lifecycle)
- ✅ Weather MCP server (enabled by default)
- ⏸️ Oracle SQLcl MCP server (disabled - requires Oracle DB)
- ✅ SCC bindings and security configurations

### Production Installation with Oracle Database

```bash
# 1. First deploy Oracle database (if needed)
helm install oracle-db ../oracle23ai/helm --namespace <your-namespace>

# 2. Wait for Oracle to be ready
kubectl wait --for=condition=ready pod/oracle23ai-0 --timeout=600s -n <your-namespace>

# 3. Enable Oracle SQLcl MCP server in values
# Edit values.yaml to set: mcp-servers.oracle-sqlcl.mcpserver.enabled: true

# 4. Deploy MCP servers with Oracle support
helm install mcp-servers ./helm --namespace <your-namespace> \
  --set mcp-servers.oracle-sqlcl.mcpserver.enabled=true \
  --set mcp-servers.mcp-weather.mcpserver.env.TAVILY_API_KEY="your-api-key"
```

## Configuration

### Architecture Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `toolhive.crds.enabled` | Install Toolhive CRDs | `true` |
| `toolhive.operator.enabled` | Deploy Toolhive operator | `true` |
| `toolhive-operator.operator.resources` | Operator resource limits | See values.yaml |

### MCP Servers Configuration

This chart uses a **dynamic, configuration-driven approach** where all MCP servers are automatically generated from the `mcp-servers` section in values.yaml.

#### Key Innovation: Zero-Template Changes Required

Adding new MCP servers requires **only configuration changes** - no template modifications needed:

- **Dynamic Resource Generation**: Templates automatically iterate over your configuration
- **Unified Structure**: All servers use the same `mcpserver` configuration pattern
- **Automatic Features**: SCC bindings, monitoring commands, and documentation are auto-generated

#### Configuration Reference

**See `helm/values.yaml` for complete configuration examples** including:

- **Weather MCP Server**: SSE transport with API key configuration
- **Oracle SQLcl MCP Server**: stdio transport with persistence and secrets
- **Toolhive Integration**: Permission profiles and resource management

**Core Configuration Pattern:**
```yaml
mcp-servers:
  <server-name>:
    mcpserver:
      enabled: true
      image: "registry/image:tag"
      port: 8080
      transport: "stdio|sse"
      # ... see values.yaml for complete examples
```

#### Supported Features

- **Transport Protocols**: Both `stdio` and `sse` via ToolHive proxy
- **Secret Management**: Secure credential injection via `envSecrets`
- **Persistent Storage**: Optional volumes and PVCs
- **Security Contexts**: Restricted permissions and SCC bindings
- **Resource Limits**: CPU and memory management
- **Auto-Discovery**: Dynamic service naming and health endpoints

## Security
### Credential Management

This chart implements secure credential management:

- **No hardcoded passwords**: All sensitive data sourced from Kubernetes secrets
- **Secret references**: Uses `envSecrets` pattern for secure credential injection
- **Oracle integration**: Leverages Oracle database's own secret for credentials
- **API key management**: Allows secure injection of external API keys

### Security Context

All containers run with restricted security contexts:
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`
- Proper service account permissions

## Monitoring

### Check MCP Server Status

```bash
# List all MCP servers
oc get mcpservers

# Check specific server status
oc describe mcpserver oracle-sqlcl

# View server logs
oc logs -l toolhive-name=oracle-sqlcl
```

### Health Endpoints

MCP servers expose health endpoints through Toolhive proxy:
- Health: `http://<service>:8080/health`
- SSE: `http://<service>:8080/sse`
- JSON-RPC: `http://<service>:8080/messages`

## Troubleshooting

### Common Issues

1. **Pod Restarts**: Check health probe timing for database connections
2. **Secret Not Found**: Ensure Oracle secret exists before installing
3. **Toolhive Operator OOMKilled**: Increase memory limits to 1Gi (default 128Mi is insufficient)
4. **MCP Server Pods Not Starting**: Verify SCC permissions were automatically created by checking ClusterRoleBindings
5. **Permission Denied**: Check that SCC bindings exist with `oc get clusterrolebindings | grep mcp-servers`
7. **Oracle Platform Compatibility**: Oracle :latest may have ORA-27350 platform issues - use 23.5.0.0 instead
8. **Oracle Security Context Issues**: Oracle requires SETUID/SETGID capabilities in SCC for proper operation
9. **Storage Issues**: Check PVC creation and storage class availability
10. **Image Pull Errors**: Check image tags and registry access

### Debug Commands

```bash
# Check Toolhive operator logs
oc logs -l app.kubernetes.io/name=toolhive-operator

# Check MCPServer resources
oc get mcpservers -o yaml

# Verify secrets
oc get secret oracle23ai -o jsonpath='{.data}' | jq 'keys'

# Check SCC permissions for service accounts (automated via ClusterRoleBindings)
oc get clusterrolebindings | grep mcp-servers
oc describe clusterrolebinding mcp-servers-toolhive-operator-anyuid
oc describe clusterrolebinding mcp-servers-mcp-weather-proxy-runner-anyuid
oc describe clusterrolebinding mcp-servers-oracle-sqlcl-proxy-runner-anyuid

# Verify MCP server deployments and pods
oc get deployments -l toolhive=true
oc get pods -l toolhive=true
oc describe pod -l toolhive-name=mcp-weather
oc describe pod -l toolhive-name=oracle-sqlcl

# Oracle-specific troubleshooting
oc logs oracle23ai-0 | grep -E "(ORA-27350|cannot set groups)"
oc get scc oracle23ai-scc -o jsonpath='{.allowedCapabilities}'
oc describe scc oracle23ai-scc | grep -A 5 "Required Drop Capabilities"
```

## Adding New MCP Servers

**The power of our optimized architecture**: Adding new MCP servers is entirely configuration-driven.

### Process (3 Simple Steps)

1. **Add configuration** to `values.yaml` (copy pattern from existing servers)
2. **Deploy**: `helm upgrade mcp-servers ./helm --namespace <your-namespace>`
3. **Done!** All resources auto-generated

### What Happens Automatically

- ✅ **MCPServer CRD**: Created with your configuration
- ✅ **SCC Bindings**: Service account permissions auto-generated
- ✅ **Storage**: PVCs created if persistence enabled
- ✅ **Monitoring**: Health endpoints and log commands added to NOTES
- ✅ **Security**: Restricted contexts and proper labeling applied

**Zero template changes required** - this is the result of our dynamic template optimization.

## Contributing

1. **Follow ToolHive-only approach**: All servers use MCPServer CRDs exclusively
2. **Use dynamic template patterns**: Templates automatically iterate over `mcp-servers` configuration
3. **Consolidate configuration**: All server settings go under `mcpserver` block
4. **Implement secure credential management**: Use `envSecrets` for sensitive data
5. **Add appropriate resource limits and security contexts**: Include in `mcpserver` configuration
6. **Update this README**: Document new server examples and configuration
7. **Test thoroughly**: Validate with `helm template` and `helm lint`

### Chart Architecture Principles

This chart follows these key principles established through optimization:

- **Dynamic Generation**: Templates iterate over configuration rather than hardcoding server lists
- **Unified Configuration**: All server settings consolidated under `mcpserver` blocks
- **ToolHive-Only**: Exclusively uses MCPServer CRDs for consistent deployment patterns
- **Security by Default**: Restricted security contexts and SCC permissions
- **Maintainability**: Adding new servers requires only configuration changes, no template updates

## Support

For issues and questions:
- Check Toolhive operator documentation
- Review MCPServer CRD specifications
- Verify OpenShift security requirements