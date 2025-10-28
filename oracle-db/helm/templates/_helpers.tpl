{{/*
Expand the name of the chart.
*/}}
{{- define "oracle-db.name" -}}
{{- default .Chart.Name .Values.oracle.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "oracle-db.fullname" -}}
{{- if .Values.oracle.fullnameOverride }}
{{- .Values.oracle.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.oracle.nameOverride }}
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
{{- define "oracle-db.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "oracle-db.labels" -}}
helm.sh/chart: {{ include "oracle-db.chart" . }}
{{ include "oracle-db.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "oracle-db.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oracle-db.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use for Oracle DB
*/}}
{{- define "oracle-db.serviceAccountName" -}}
{{- if .Values.oracle.serviceAccount.create }}
{{- default (include "oracle-db.fullname" .) .Values.oracle.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.oracle.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use for TPC-DS job
*/}}
{{- define "oracle-db.jobServiceAccountName" -}}
{{- if .Values.tpcds.serviceAccount.create }}
{{- default (printf "%s-job" (include "oracle-db.fullname" .)) .Values.tpcds.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.tpcds.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Oracle database connection string
*/}}
{{- define "oracle-db.connectionString" -}}
{{- printf "%s:%s/%s" .Values.tpcds.database.host .Values.tpcds.database.port .Values.tpcds.database.serviceName }}
{{- end }}

{{/*
Generate Oracle password if not provided
Uses existing secret if available, otherwise generates a stable password
*/}}
{{- define "oracle-db.oraclePassword" -}}
{{- if .Values.oracle.secret.password }}
{{- .Values.oracle.secret.password }}
{{- else }}
{{- $existingSecret := lookup "v1" "Secret" .Release.Namespace (include "oracle-db.fullname" .) }}
{{- if $existingSecret }}
{{- index $existingSecret.data "password" | b64dec }}
{{- else }}
{{- randAlphaNum 16 }}
{{- end }}
{{- end }}
{{- end }}