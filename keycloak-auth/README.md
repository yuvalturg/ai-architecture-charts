# KC-Auth Helm Chart

A minimalistic Keycloak authentication Helm chart for OpenShift that provides OAuth integration and predefined roles.

## Features

- Deploys Keycloak using upstream images
- Integrates with external database (user-provided)
- OpenShift OAuth integration
- Predefined roles (user/admin/devops)
- Automatic realm configuration
- Self-deployable with proper RBAC
- Cluster-wide resources with namespace-appended names

## Prerequisites

1. **Database**: Deploy a PostgreSQL/MySQL/MariaDB database separately
2. **Database Secret**: Create a secret containing database credentials
3. **Admin Secret**: Create a secret containing Keycloak admin password
4. **OpenShift Cluster**: Running OpenShift with OAuth enabled

## Installation

### 1. Create Required Secrets

```bash
# Database secret
kubectl create secret generic kc-auth-db-secret \
  --from-literal=database-url="jdbc:postgresql://postgres:5432/keycloak" \
  --from-literal=database-user="keycloak" \
  --from-literal=database-password="your-db-password"

# Admin password secret
kubectl create secret generic kc-auth-admin-secret \
  --from-literal=password="your-admin-password"
```

### 2. Configure Values

Create a `values-override.yaml` file:

```yaml
keycloak:
  hostname: "keycloak.apps.your-cluster.com"
  
  openshiftOAuth:
    baseUrl: "https://oauth-openshift.apps.your-cluster.com"
    oauthRedirectURIs:
      - "https://keycloak.apps.your-cluster.com/realms/openshift/broker/openshift-oauth/endpoint"
  
  appClient:
    redirectUris:
      - "https://your-app.apps.your-cluster.com/auth/callback"
    webOrigins:
      - "https://your-app.apps.your-cluster.com"

route:
  host: "keycloak.apps.your-cluster.com"
```

### 3. Deploy

```bash
helm install kc-auth ./helm -f values-override.yaml
```

## Configuration

### Database Configuration

The chart supports multiple database types:
- `postgres` (default)
- `mysql`
- `mariadb`
- `oracle`
- `mssql`

Configure via `database.type` in values.yaml.

### Predefined Roles

Three roles are created by default:
- `user`: Standard user role
- `admin`: Administrator role  
- `devops`: DevOps role

Customize via `keycloak.predefinedRoles` in values.yaml.

### OpenShift OAuth Integration

The chart automatically configures:
- OpenShift as an identity provider in Keycloak
- OAuth client for OpenShift authentication
- Proper redirect URIs and scopes

### Application Integration

For applications to authenticate against this Keycloak instance, use:

**Auth Endpoint**: `https://your-keycloak-host/realms/openshift/protocol/openid-connect/auth`
**Token Endpoint**: `https://your-keycloak-host/realms/openshift/protocol/openid-connect/token`
**Client ID**: `app-integration-client` (configurable)

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `keycloak.hostname` | Keycloak public hostname | `keycloak.example.com` |
| `keycloak.realm` | Realm name | `openshift` |
| `keycloak.adminUser` | Admin username | `admin` |
| `database.type` | Database type | `postgres` |
| `database.secret.name` | Database secret name | `kc-auth-db-secret` |
| `route.enabled` | Enable OpenShift route | `true` |
| `rbac.create` | Create RBAC resources | `true` |

## Troubleshooting

### Database Connection Issues
- Verify database secret contains correct credentials
- Check database URL format matches your database type
- Ensure database is accessible from the Keycloak pod

### OAuth Integration Issues  
- Verify OpenShift OAuth endpoints are correct
- Check OAuthClient was created successfully
- Ensure redirect URIs match exactly

### Permission Issues
- Verify ServiceAccount has proper ClusterRole permissions
- Check that RBAC resources were created successfully

## Uninstalling

```bash
helm uninstall kc-auth
```

Note: This will not delete cluster-wide resources automatically. Clean them up manually if needed:

```bash
kubectl delete clusterrole kc-auth-<namespace>
kubectl delete clusterrolebinding kc-auth-<namespace>
kubectl delete oauthclient kc-auth-<namespace>
```