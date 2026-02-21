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

{{/*
Get root CA certificate from cert-manager
SECURITY: This properly validates TLS instead of using insecureSkipVerify
Never use insecureSkipVerify in production - it allows MITM attacks!
*/}}
{{- define "argocd-config.rootCA" -}}
{{- $secret := lookup "v1" "Secret" "cert-manager" "vectorweight-root-ca" -}}
{{- if $secret -}}
{{- $secret.data.tls\.crt | b64dec -}}
{{- else -}}
-----BEGIN CERTIFICATE-----
MIIDLzCCAhegAwIBAgIUAJl2xR1OaKfgTNTC4KhjdhTa2ugwDQYJKoZIhvcNAQEL
BQAwHzEdMBsGA1UEAxMUVmVjdG9yV2VpZ2h0IFJvb3QgQ0EwHhcNMjYwMTE2MDIw
MzEwWhcNMjYwNDE2MDIwMzEwWjAfMR0wGwYDVQQDExRWZWN0b3JXZWlnaHQgUm9v
dCBDQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMWHfGxb8gEMsQP8
2b/OP2oiHuU74SpYgn+u3HjR5xIm7PcWvSsHRyzTh4Fs8pXKHDozLFqq/h0fBZED
S9qtUUpUGls7QozS4uw2YVDZM5mSux6AVmO2azOj/dTeYpYPeWuF9sEKyCJnvXZn
OGr0FLFJdnfr52NOAM+5o/Gvo12/D5bngmFLaEJ6KiqXSjfws1LXL9SP6EOdIFQG
L3Ip9xyd/2R5YZ/eIyUGoyN05s9tHV3RnkKqdgGnFiugeZC15C2M+E98ZWAw4dZ9
4Xaw/RaHWCAryoZ7NCDcTIMIijwSrZsGuGnDoJVYOequYgpOD73uAJXMUyYxS84I
X6F5WhUCAwEAAaNjMGEwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB/wQFMAMBAf8w
HQYDVR0OBBYEFOI9nPgQjludFdUF+FBPGINnnwMaMB8GA1UdEQQYMBaCFFZlY3Rv
cldlaWdodCBSb290IENBMA0GCSqGSIb3DQEBCwUAA4IBAQBP5EdftFWqUHyFDxog
TY6U3sXk55OWzKa8etS/wGBIeGGwxZDVP2I9xtwQDDRAR3s7aV7fQcNnOXFBOkpl
SiX8mypmRes5DR+82ESgahFyRAf+FANEz+u5w2QBopaOmr/MltnfR6s03oPGc64v
gOKvrPm2fiVOMe5cZ32bNtEhaPAHzMeT5Ha7qPsT2FEj6Nr9LnlRiQajYEy11pPz
AlCKtfrphtzjlvDnPkRekM/jVmAXJkGn+gAXjLX4kIJ6RdtwSZHMt0kOuPWWzlTA
lvHMGGrwmOpWjSEB+lhDIqQ5oQwG+kVwJIKk9wGO0Hp3qJQ1SMpBYKyyyQKTVymn
N3eW
-----END CERTIFICATE-----
{{- end -}}
{{- end -}}
