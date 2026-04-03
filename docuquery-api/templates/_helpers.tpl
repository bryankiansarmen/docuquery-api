 {{/* vim: set filetype=mustache: */}}
 {{/*
 Expand the name of the chart.
 */}}
 {{- define "name" -}}
 {{/*
 {{- default .Chart.Name .Release.Namespace | trunc 63 | trimSuffix "-" -}}
 */}}
 {{- printf "%s-%s" .Chart.Name .Release.Namespace | trunc 63 | trimSuffix "-" -}}
 {{- end -}}
 
 {{/*
 Create a Kubernetes resource name
 We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
 It contains of name and if --set colour=whatever is defined then the resource will be coloured
 */}}
 {{- define "resourceName" -}}
 {{- $name := default .Chart.Name .Values.nameOverride -}}
 {{- if .Values.colour -}}
 {{- printf "%s-%s" $name  .Values.colour | trunc 63 | trimSuffix "-" -}}
 {{- else -}}
 {{- printf "%s" $name  | trunc 63 | trimSuffix "-" -}}
 {{- end -}}
 {{- end -}}
 
 
 {{/*
 Create a default fully qualified app name.
 We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
 If release name contains chart name it will be used as a full name.
 */}}
 {{- define "fullname" -}}
 {{- $name := default .Chart.Name .Values.nameOverride -}}
 {{- if .Values.colour -}}
 {{- printf "%s-%s" $name  .Values.colour | trunc 63 | trimSuffix "-" -}}
 {{- else -}}
 {{- printf "%s" $name  | trunc 63 | trimSuffix "-" -}}
 {{- end -}}
 {{- end -}}
 
 {{/*
 Create chart name and version as used by the chart label.
 */}}
 {{- define "chart" -}}
 {{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
 {{- end -}}
