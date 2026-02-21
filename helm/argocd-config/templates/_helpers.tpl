{{/*
Get OIDC client secret from argocd-oidc-secret
*/}}
{{- define "argocd-config.oidcClientSecret" -}}
{{- $secret := lookup "v1" "Secret" "argocd" "argocd-oidc-secret" -}}
{{- if $secret -}}
{{- $secret.data.clientSecret | b64dec -}}
{{- else -}}
placeholder-run-setup-keycloak-realm-sh-first
{{- end -}}
{{- end -}}
