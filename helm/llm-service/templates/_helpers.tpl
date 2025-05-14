{{- define "llm-service.mergeModels" -}}
  {{- $globalModels := .Values.global | default dict }}
  {{- $globalModels := $globalModels.models | default dict }}
  {{- $localModels := .Values.models | default dict }}
  {{- $merged := merge $globalModels $localModels }}
  {{- toJson $merged }}
{{- end }}

{{- define "llm-service.deployModels" -}}
  {{- $deployModels := dict }}
  {{- range $key, $model := . }}
    {{- if and $model.enabled (not $model.url) }}
      {{- $_ := set $deployModels $key $model }}
    {{- end }}
  {{- end }}
  {{- toJson $deployModels }}
{{- end }}