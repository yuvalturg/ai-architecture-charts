# Keycloak Authentication and RBAC Helm Chart

This Helm chart deploys Keycloak with OpenShift OAuth integration for authentication and role-based access control (RBAC). It's designed to be used as a central authentication service for other applications in your OpenShift cluster.

## Features

- **Keycloak Deployment**: Based on Bitnami's Keycloak Helm chart
- **OpenShift OAuth Integration**: Seamless integration with OpenShift's built-in OAuth provider
- **Role-Based Access Control**: Configurable roles and group mappings
- **Automated Realm Configuration**: Automatic setup of realm, identity providers, and clients
- **Production Ready**: Includes PostgreSQL, TLS, monitoring, and security configurations
- **Extensible**: Easy to configure for use with other applications

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- Cluster admin privileges (for OAuth client creation)

## Installation

### 1. Add the chart repository

```bash
helm repo add ai-architecture https://rhkp.github.io/ai-architecture-charts
helm repo update
```

### 2. Create a namespace

```bash
oc new-project keycloak-auth
```

### 3. Install the chart

#### Basic installation:

```bash
helm install keycloak-auth ai-architecture/keycloak-auth \
  --set keycloak.ingress.hostname=keycloak.apps.your-cluster.com
```

#### Production installation with custom values:

```bash
helm install keycloak-auth ai-architecture/keycloak-auth \
  --values custom-values.yaml
```

## Configuration

### Required Configuration

You **must** configure the following values for your environment:

```yaml
keycloak:
  ingress:
    hostname: "keycloak.apps.your-cluster.com"  # Your Keycloak hostname

global:
  openshift:
    oauth:
      redirectURIs:
        - "https://keycloak.apps.your-cluster.com/realms/openshift/broker/openshift-v4/endpoint"
```

### OpenShift OAuth Configuration

The chart automatically creates an OAuth client in OpenShift. Configure the OAuth settings:

```yaml
global:
  openshift:
    enabled: true
    oauth:
      clientName: "keycloak-openshift-oauth"
      redirectURIs:
        - "https://keycloak.apps.your-cluster.com/realms/openshift/broker/openshift-v4/endpoint"
      grantMethod: "auto"
      scopes:
        - "user:info"
        - "user:check-access"
        - "user:list-projects"
```

### RBAC and Role Configuration

Configure initial roles that will be created in Keycloak:

```yaml
rbac:
  enabled: true
  roles:
    - name: "admin"
      description: "Administrator role with full access to all resources"
      attributes:
        permissions: ["*"]
    - name: "user"
      description: "Standard user role with basic access"
      attributes:
        permissions: ["read", "basic"]
    - name: "devops"
      description: "DevOps role with deployment and infrastructure management access"
      attributes:
        permissions: ["read", "write", "deploy", "manage-infrastructure"]
```

**Note**: These roles are created automatically during installation. You can then manually assign these roles to users through the Keycloak admin console.

### Application Clients

Configure clients for applications that will use this Keycloak:

```yaml
clients:
  enabled: true
  default:
    - clientId: "my-app"
      name: "My Application"
      description: "My Application Client"
      enabled: true
      redirectUris:
        - "https://my-app.apps.your-cluster.com/*"
      webOrigins:
        - "https://my-app.apps.your-cluster.com"
      publicClient: false
      standardFlowEnabled: true
      directAccessGrantsEnabled: true
```

### Production Configuration

For production deployments, configure:

```yaml
keycloak:
  production: true
  proxy: "edge"
  
  # Use external PostgreSQL
  postgresql:
    enabled: true
    auth:
      postgresPassword: "your-secure-password"
      password: "your-secure-password"
    primary:
      persistence:
        enabled: true
        size: 20Gi
        
  # Resource limits
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
      
  # TLS configuration
  ingress:
    enabled: true
    tls: true
    selfSigned: false
```

## Role Management

This chart uses **manual role management** through the Keycloak admin console:

### 1. Access Keycloak Admin Console

```bash
# Get the Keycloak admin URL
echo "Admin URL: https://$(oc get route keycloak-auth-keycloak -o jsonpath='{.spec.host}')/admin"

# Get admin credentials
echo "Username: admin"
echo "Password: $(oc get secret keycloak-auth-admin -o jsonpath='{.data.admin-password}' | base64 -d)"
```

### 2. Assign Roles to Users

1. Login to the admin console with the credentials above
2. Navigate to your realm (default: `openshift`)
3. Go to **Users** → [Select User] → **Role Mappings**
4. Assign realm roles as needed (admin, user, devops)

### 3. How Authentication Works

1. **User logs in via OpenShift OAuth** to Keycloak
2. **Keycloak authenticates** the user against OpenShift
3. **Keycloak checks manually assigned roles** for that specific user
4. **Applications receive JWT tokens** with the assigned roles

This gives you complete control over user permissions without automatic group synchronization.

## Using the Chart with Other Applications

Once deployed, other applications can use this Keycloak for authentication:

### 1. Get Integration Information

```bash
# Get the Keycloak URL
echo "Keycloak URL: https://$(oc get route keycloak-auth-keycloak -o jsonpath='{.spec.host}')"
echo "Issuer URL: https://$(oc get route keycloak-auth-keycloak -o jsonpath='{.spec.host}')/realms/openshift"
```

### 2. Configure Your Application

Configure your application to use Keycloak as an OIDC provider:

- **Issuer URL**: `https://keycloak.apps.your-cluster.com/realms/openshift`
- **Client ID**: The client ID you configured in the `clients` section
- **Client Secret**: Retrieved from Keycloak admin console

### 3. Example Application Integration

For a web application, configure OIDC:

```yaml
# In your application's values.yaml
auth:
  enabled: true
  oidc:
    issuerUrl: "https://keycloak.apps.your-cluster.com/realms/openshift"
    clientId: "my-app"
    clientSecret: "client-secret-from-keycloak"
```

## Monitoring

Enable monitoring with Prometheus:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: "30s"
    labels:
      monitoring: "prometheus"
```

## Security

The chart includes several security features:

- **Non-root containers**: All containers run as non-root users
- **Network policies**: Optional network isolation
- **Secret management**: Automatic generation of secure passwords
- **TLS**: Full TLS support for production deployments

## Troubleshooting

### Common Issues

1. **OAuth Client Creation Fails**
   - Ensure you have cluster admin privileges
   - Check that the OAuth client name is unique

2. **Realm Import Fails**
   - Check Keycloak logs: `oc logs -l app.kubernetes.io/name=keycloak`
   - Verify admin credentials are correct

3. **Group Sync Fails**
   - Ensure OpenShift groups exist
   - Check RBAC permissions for the service account

### Logs

View logs for different components:

```bash
# Keycloak logs
oc logs -l app.kubernetes.io/name=keycloak

# Realm import job logs
oc logs job/keycloak-auth-realm-import

# Group sync job logs
oc logs job/keycloak-auth-group-sync
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade keycloak-auth ai-architecture/keycloak-auth \
  --values your-values.yaml
```

## Uninstalling

To uninstall the chart:

```bash
helm uninstall keycloak-auth
```

**Note**: This will also remove the OAuth client from OpenShift.

## Values Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `global.openshift.enabled` | bool | `true` | Enable OpenShift integration |
| `global.openshift.oauth.clientName` | string | `"keycloak-openshift-oauth"` | OAuth client name |
| `keycloak.enabled` | bool | `true` | Enable Keycloak deployment |
| `keycloak.auth.adminUser` | string | `"admin"` | Keycloak admin username |
| `keycloak.ingress.hostname` | string | `"keycloak.example.com"` | Keycloak hostname |
| `realm.enabled` | bool | `true` | Enable realm creation |
| `realm.name` | string | `"openshift"` | Realm name |
| `rbac.enabled` | bool | `true` | Enable RBAC configuration |
| `clients.enabled` | bool | `true` | Enable client creation |

For a complete list of values, see [values.yaml](helm/values.yaml).

## Contributing

Contributions are welcome! Please read the [Contributing Guide](../CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.