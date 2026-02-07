{{/*
AEGIS Helm Chart Helper Templates
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "aegis.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this.
*/}}
{{- define "aegis.fullname" -}}
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
{{- define "aegis.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "aegis.labels" -}}
helm.sh/chart: {{ include "aegis.chart" . }}
{{ include "aegis.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "aegis.selectorLabels" -}}
app.kubernetes.io/name: {{ include "aegis.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: operator
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "aegis.serviceAccountName" -}}
{{- if .Values.operator.serviceAccount.create }}
{{- default (printf "%s-operator" (include "aegis.fullname" .)) .Values.operator.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.operator.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the namespace name
*/}}
{{- define "aegis.namespace" -}}
{{- default "aegis-system" .Values.namespace.name }}
{{- end }}

{{/*
Create the operator image
*/}}
{{- define "aegis.operatorImage" -}}
{{- $tag := default .Chart.AppVersion .Values.operator.image.tag }}
{{- printf "%s:%s" .Values.operator.image.repository $tag }}
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "aegis.configMapName" -}}
{{- printf "%s-config" (include "aegis.fullname" .) }}
{{- end }}
