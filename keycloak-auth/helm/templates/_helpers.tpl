{{/*
Expand the name of the chart.
*/}}
{{- define "keycloak-auth.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "keycloak-auth.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "keycloak-auth.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "keycloak-auth.labels" -}}
helm.sh/chart: {{ include "keycloak-auth.chart" . }}
{{ include "keycloak-auth.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "keycloak-auth.selectorLabels" -}}
app.kubernetes.io/name: {{ include "keycloak-auth.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "keycloak-auth.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "keycloak-auth.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get the Keycloak admin password secret name
*/}}
{{- define "keycloak-auth.adminPasswordSecretName" -}}
{{- if .Values.keycloak.auth.existingSecret }}
{{- .Values.keycloak.auth.existingSecret }}
{{- else }}
{{- printf "%s-admin" (include "keycloak-auth.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Get the realm name
*/}}
{{- define "keycloak-auth.realmName" -}}
{{- .Values.realm.name | default "openshift" }}
{{- end }}

{{/*
Generate the Keycloak hostname automatically
*/}}
{{- define "keycloak-auth.hostname" -}}
{{- if .Values.keycloak.ingress.hostname }}
{{- .Values.keycloak.ingress.hostname }}
{{- else }}
{{- printf "%s-keycloak.%s.svc.cluster.local" .Release.Name .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Generate the full Keycloak URL
*/}}
{{- define "keycloak-auth.url" -}}
{{- if .Values.keycloak.ingress.enabled }}
{{- if .Values.keycloak.ingress.tls }}
{{- printf "https://%s" (include "keycloak-auth.hostname" .) }}
{{- else }}
{{- printf "http://%s" (include "keycloak-auth.hostname" .) }}
{{- end }}
{{- else }}
{{- printf "http://%s:8080" (include "keycloak-auth.hostname" .) }}
{{- end }}
{{- end }}

{{/*
Generate OAuth redirect URI automatically
*/}}
{{- define "keycloak-auth.oauthRedirectURI" -}}
{{- printf "%s/realms/%s/broker/openshift-v4/endpoint" (include "keycloak-auth.url" .) (include "keycloak-auth.realmName" .) }}
{{- end }}

{{/*
Generate OAuth client secret
*/}}
{{- define "keycloak-auth.oauthClientSecret" -}}
{{- randAlphaNum 32 | b64enc }}
{{- end }}

{{/*
Generate realm import JSON
*/}}
{{- define "keycloak-auth.realmConfig" -}}
{
  "realm": "{{ include "keycloak-auth.realmName" . }}",
  "displayName": "{{ .Values.realm.displayName }}",
  "enabled": {{ .Values.realm.realmEnabled }},
  "registrationAllowed": {{ .Values.realm.registrationAllowed }},
  "rememberMe": {{ .Values.realm.rememberMe }},
  "verifyEmail": {{ .Values.realm.verifyEmail }},
  "loginWithEmailAllowed": {{ .Values.realm.loginWithEmailAllowed }},
  "duplicateEmailsAllowed": {{ .Values.realm.duplicateEmailsAllowed }},
  "resetPasswordAllowed": {{ .Values.realm.resetPasswordAllowed }},
  "editUsernameAllowed": {{ .Values.realm.editUsernameAllowed }},
  "sslRequired": "{{ .Values.realm.sslRequired }}",
  {{- if .Values.realm.identityProvider.enabled }}
  "identityProviders": [
    {
      "alias": "{{ .Values.realm.identityProvider.alias }}",
      "displayName": "{{ .Values.realm.identityProvider.displayName }}",
      "providerId": "{{ .Values.realm.identityProvider.providerId }}",
      "enabled": true,
      "trustEmail": {{ .Values.realm.identityProvider.trustEmail }},
      "storeToken": {{ .Values.realm.identityProvider.storeToken }},
      "addReadTokenRoleOnCreate": {{ .Values.realm.identityProvider.addReadTokenRoleOnCreate }},
      "authenticateByDefault": {{ .Values.realm.identityProvider.authenticateByDefault }},
      "linkOnly": {{ .Values.realm.identityProvider.linkOnly }},
      "firstBrokerLoginFlowAlias": "{{ .Values.realm.identityProvider.firstBrokerLoginFlowAlias }}",
      "config": {
        "clientId": "{{ .Values.global.openshift.oauth.clientName }}",
        "clientSecret": "${OPENSHIFT_OAUTH_CLIENT_SECRET}",
        "baseUrl": "${OPENSHIFT_API_URL}",
        "useJwksUrl": "true"
      }
    }
  ],
  {{- end }}
  {{- if .Values.rbac.enabled }}
  "roles": {
    "realm": [
      {{- range $index, $role := .Values.rbac.roles }}
      {{- if $index }},{{- end }}
      {
        "name": "{{ $role.name }}",
        "description": "{{ $role.description }}",
        "composite": {{ $role.composite }},
        "attributes": {{ $role.attributes | toJson }}
      }
      {{- end }}
    ]
  },
  {{- end }}
  {{- if .Values.clients.enabled }}
  "clients": [
    {{- range $index, $client := .Values.clients.default }}
    {{- if $index }},{{- end }}
    {
      "clientId": "{{ $client.clientId }}",
      "name": "{{ $client.name }}",
      "description": "{{ $client.description }}",
      "enabled": {{ $client.enabled }},
      "clientAuthenticatorType": "{{ $client.clientAuthenticatorType }}",
      "redirectUris": {{ $client.redirectUris | toJson }},
      "webOrigins": {{ $client.webOrigins | toJson }},
      "publicClient": {{ $client.publicClient }},
      "serviceAccountsEnabled": {{ $client.serviceAccountsEnabled }},
      "authorizationServicesEnabled": {{ $client.authorizationServicesEnabled }},
      "standardFlowEnabled": {{ $client.standardFlowEnabled }},
      "implicitFlowEnabled": {{ $client.implicitFlowEnabled }},
      "directAccessGrantsEnabled": {{ $client.directAccessGrantsEnabled }}
    }
    {{- end }}
  ]
  {{- end }}
}
{{- end }}