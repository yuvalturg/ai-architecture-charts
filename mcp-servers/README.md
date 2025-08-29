# MCP Servers Helm Chart

This Helm chart deploys MCP (Model Context Protocol) servers that provide external tools and capabilities to AI models. MCP servers enable AI agents to interact with external systems, APIs, and services.

## Overview

The mcp-servers chart creates:
- Deployments for various MCP server implementations
- Services for MCP server endpoints
- ConfigMaps for server configuration
- Support for multiple MCP server types
- Integration with LlamaStack and other AI services

## Prerequisites

- OpenShift cluster
- Helm 3.x
- Access to container registries
- Network connectivity to external APIs (if used by MCP servers)

## Installation

### Basic Installation

```bash
helm install mcp-servers ./helm
```

### Installation with Weather MCP Server

```bash
helm install mcp-servers ./helm \
  --set mcp-servers.mcp-weather.deploy=true
```

### Installation with Custom Namespace

```bash
helm install mcp-servers ./helm \
  --namespace mcp-servers \
  --create-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mcp-servers.mcp-weather.deploy` | Deploy weather MCP server | `false` |
| `mcp-servers.mcp-weather.imageRepository` | Weather server image repository | `quay.io/ecosystem-appeng/mcp-weather` |
| `mcp-servers.mcp-weather.uri` | Weather server URI endpoint | `http://mcp-weather:8000/sse` |

### MCP Server Configuration

#### Weather MCP Server
```yaml
mcp-servers:
  mcp-weather:
    deploy: true
    imageRepository: quay.io/ecosystem-appeng/mcp-weather
    imageTag: latest
    uri: http://mcp-weather:8000/sse
    port: 8000
    replicas: 1
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "512Mi"
        cpu: "200m"
```

### Complete Example values.yaml

```yaml
mcp-servers:
  mcp-weather:
    deploy: true
    imageRepository: quay.io/ecosystem-appeng/mcp-weather
    imageTag: v1.0.0
    uri: http://mcp-weather:8000/sse
    port: 8000
    replicas: 2
    
    # Environment variables for weather API
    env:
      - name: WEATHER_API_KEY
        valueFrom:
          secretKeyRef:
            name: weather-api-secret
            key: api-key
      - name: WEATHER_DEFAULT_LOCATION
        value: "New York, NY"
    
    # Resource limits
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"
      limits:
        memory: "1Gi"
        cpu: "500m"
    
    # Health check configuration
    healthCheck:
      enabled: true
      path: /health
      initialDelaySeconds: 30
      periodSeconds: 10
    
    # Service configuration
    service:
      type: ClusterIP
      port: 8000
      targetPort: 8000

  # Example: Additional MCP server
  mcp-database:
    deploy: false
    imageRepository: quay.io/your-org/mcp-database
    imageTag: v1.0.0
    uri: http://mcp-database:8000/sse
    port: 8000
```

## Usage

### Accessing MCP Server Endpoints

MCP servers expose Server-Sent Events (SSE) endpoints for real-time communication:

```bash
# Check MCP server status
oc get pods -l app.kubernetes.io/name=mcp-servers

# Get service endpoints
oc get svc -l app.kubernetes.io/name=mcp-servers

# Port forward for local testing
oc port-forward svc/mcp-weather 8000:8000

# Test MCP weather server endpoint
curl -X GET http://localhost:8000/health
```

### SSE Endpoint Testing

```bash
# Connect to SSE endpoint
curl -N -H "Accept: text/event-stream" \
  http://localhost:8000/sse

# Test weather query capability
curl -X POST http://localhost:8000/tools/weather \
  -H "Content-Type: application/json" \
  -d '{
    "location": "New York, NY",
    "units": "metric"
  }'
```

### Integration with LlamaStack

Configure LlamaStack to use MCP servers:

```yaml
# In LlamaStack configuration
mcp-servers:
  weather-server:
    endpoint: "http://mcp-weather:8000/sse"
    capabilities:
      - weather_lookup
      - location_search
    timeout: 30s
```

### OpenShift Routes

Create routes for external access:

```bash
# Expose weather MCP server
oc expose service mcp-weather
oc get routes mcp-weather
```

## MCP Server Development

### Creating Custom MCP Servers

To add a new MCP server to the chart:

1. **Add server configuration in values.yaml:**
```yaml
mcp-servers:
  mcp-custom:
    deploy: true  # Set to true to enable deployment
    imageRepository: quay.io/your-org/mcp-custom
    imageTag: v1.0.0
    uri: http://mcp-custom:8000/sse
    port: 8000
```

The chart will automatically generate the deployment, service, and other resources when `deploy: true`. No additional templates are required.

### Building and Publishing Custom MCP Servers

For MCP servers that require custom builds, you can place them under this package and configure them to be built and pushed to Quay.io:

1. **Create server directory structure:**
```
mcp-servers/
├── your-server-name/
│   ├── Containerfile
│   └── src/
│       ├── server.py
│       └── requirements.txt
└── helm/
    └── values.yaml
```

2. **Add to GitHub workflow matrix:**
Edit `.github/workflows/publish-helm-charts.yaml` and add your server to the build matrix:
```yaml
strategy:
  matrix:
    include:
      - name: mcp-weather
        file: mcp-servers/weather/Containerfile
        context: mcp-servers/weather/src
        chart: mcp-servers/helm/Chart.yaml
      - name: your-server-name  # Add your server here
        file: mcp-servers/your-server-name/Containerfile
        context: mcp-servers/your-server-name/src
        chart: mcp-servers/helm/Chart.yaml
```

3. **Configure in values.yaml:**
```yaml
mcp-servers:
  your-server-name:
    deploy: true
    imageRepository: quay.io/ecosystem-appeng/your-server-name
    # imageTag will be set from chart version
    uri: http://your-server-name:8000/sse
    port: 8000
```

The GitHub workflow will build the container image from your Containerfile and push it to `quay.io/ecosystem-appeng/your-server-name` with the version from the MCP Servers helm chart.

### MCP Protocol Implementation

MCP servers should implement the Model Context Protocol specification:

```python
# Example Python MCP server structure
from mcp_server import MCPServer
import asyncio

class CustomMCPServer(MCPServer):
    def __init__(self):
        super().__init__()
        self.register_tool("custom_tool", self.handle_custom_tool)
    
    async def handle_custom_tool(self, params):
        # Implement tool logic
        return {"result": "Custom tool response"}
    
    async def start_server(self):
        # Start SSE endpoint
        await self.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    server = CustomMCPServer()
    asyncio.run(server.start_server())
```

## Monitoring and Troubleshooting

### Checking Service Health

```bash
# Check all MCP server pods
oc get pods -l app.kubernetes.io/name=mcp-servers

# Check specific MCP server
oc get pods -l app=mcp-weather

# Check service status
oc get svc mcp-weather

# Test health endpoint
oc exec -it deployment/mcp-weather -- curl localhost:8000/health
```

### Viewing Logs

```bash
# View weather server logs
oc logs -l app=mcp-weather -f

# View all MCP server logs
oc logs -l app.kubernetes.io/name=mcp-servers -f

# Debug connection issues
oc describe pod -l app=mcp-weather
```

### Common Issues

1. **Server Not Starting**:
   - Check container image availability
   - Verify environment variables
   - Check resource limits
   - Review container logs

2. **SSE Connection Issues**:
   - Verify port configuration
   - Check service networking
   - Test endpoint accessibility
   - Validate SSE implementation

3. **External API Integration**:
   - Check API key configuration
   - Verify network connectivity
   - Review rate limiting
   - Validate API endpoint accessibility

4. **Performance Issues**:
   - Monitor resource usage
   - Check connection pooling
   - Review timeout settings
   - Optimize response handling

### Debugging Commands

```bash
# Check container environment
oc exec -it deployment/mcp-weather -- env

# Test internal connectivity
oc exec -it deployment/mcp-weather -- wget -O- http://localhost:8000/health

# Check network policies
oc get networkpolicies

# Inspect service endpoints
oc describe endpoints mcp-weather
```

## Security Considerations

### API Key Management

```bash
# Create secret for API keys
oc create secret generic weather-api-secret \
  --from-literal=api-key=your_weather_api_key

# Use in MCP server configuration
env:
  - name: WEATHER_API_KEY
    valueFrom:
      secretKeyRef:
        name: weather-api-secret
        key: api-key
```


## Integration Examples

### Weather Service Integration

```yaml
# Weather MCP server with full configuration
mcp-servers:
  mcp-weather:
    deploy: true
    imageRepository: quay.io/ecosystem-appeng/mcp-weather
    
    env:
      - name: OPENWEATHER_API_KEY
        valueFrom:
          secretKeyRef:
            name: openweather-secret
            key: api-key
      - name: DEFAULT_UNITS
        value: "metric"
      - name: CACHE_TTL
        value: "300"
    
    capabilities:
      - current_weather
      - weather_forecast
      - weather_alerts
      - location_search
```

### Database Query Server

```yaml
mcp-servers:
  mcp-database:
    deploy: true
    imageRepository: quay.io/your-org/mcp-database
    
    env:
      - name: DB_CONNECTION_STRING
        valueFrom:
          secretKeyRef:
            name: database-secret
            key: connection-string
      - name: QUERY_TIMEOUT
        value: "30s"
      - name: MAX_RESULTS
        value: "1000"
```

## Upgrading

```bash
# Upgrade with new image versions
helm upgrade mcp-servers ./helm \
  --set mcp-servers.mcp-weather.imageTag=v2.0.0

# Check rollout status
oc rollout status deployment/mcp-weather
```

## Uninstalling

```bash
# Remove chart
helm uninstall mcp-servers

# Clean up secrets (if needed)
oc delete secret weather-api-secret openweather-secret

# Remove persistent data (if any)
oc delete pvc -l app.kubernetes.io/name=mcp-servers
```


## Advanced Configuration

### Custom Protocol Support

```yaml
mcp-servers:
  mcp-custom:
    protocol:
      version: "2024-11-05"
      features:
        - server-sent-events
        - bidirectional-streams
        - tool-calling
    
    middleware:
      - authentication
      - rate-limiting
      - request-logging
```

### Multi-Environment Deployment

```bash
# Development environment
helm install mcp-servers-dev ./helm \
  --namespace development \
  --set mcp-servers.mcp-weather.imageTag=dev

# Production environment
helm install mcp-servers-prod ./helm \
  --namespace production \
  --set mcp-servers.mcp-weather.imageTag=v1.0.0 \
  --set mcp-servers.mcp-weather.replicas=3
```