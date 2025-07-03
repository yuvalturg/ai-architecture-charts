{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mcp-servers.chart" -}}
{{- printf "%s-%s" .root.Chart.Name .root.Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mcp-servers.labels" -}}
helm.sh/chart: {{ include "mcp-servers.chart" . }}
{{ include "mcp-servers.selectorLabels" . }}
{{- if .root.Chart.AppVersion }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mcp-servers.selectorLabels" -}}
app.kubernetes.io/name: {{ .key }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mcp-servers.serviceAccountName" -}}
{{- if (default false .server.createServiceAccount) }}
{{- .server.serviceAccountName | default .key }}
{{- else }}
{{- .server.serviceAccountName | default "default" }}
{{- end }}
{{- end }}

{{- define "mcp-servers.mergeMcpServers" -}}
  {{- $globalServers := .Values.global | default dict }}
  {{- $globalServers := index $globalServers "mcp-servers" | default dict }}
  {{- $localServers := index .Values "mcp-servers" | default dict }}
  {{- $merged := merge $globalServers $localServers }}
  {{- toJson $merged }}
{{- end }}