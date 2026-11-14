# Feature: api-auth

**Keywords:** oauth2, introspection, DiodeOAuth2Authentication, require_scopes, netbox:read, netbox:write, diode_username, token-cache
**Arquivos principais:**
  - netbox_diode_plugin/api/authentication.py
  - netbox_diode_plugin/api/permissions.py
  - netbox_diode_plugin/provisioning.py
**Resumo:** Autenticação reconciler→plugin por Bearer token OAuth2 validado por introspecção no Diode Auth, com cache Redis e escopos por endpoint.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2213-hardening-auth-introspeccao | TTL por exp-now, is_active, aud string | aceitação de token vencido
- SPEC-20261113-2214-allowlist-tipos-gravaveis | ObjectPermissions opcionais | menor privilégio

## Estado atual

O token é introspectado com POST no Diode Auth (`timeout=5`), e o resultado (incluindo o objeto `User`) é cacheado em `diode:oauth2:introspect:<sha256>` com TTL `exp - iat` (`authentication.py:95-99`). `aud` é tratado como lista (`:83`). `IsAuthenticated` só checa `is_authenticated` (`permissions.py:11-16`). Os escopos `netbox:read`/`netbox:write` são aplicados por `require_scopes`.

## Decisões arquiteturais ativas
- DEC-20261113-2154-introspeccao-mantida [ativa] (SPEC-20261113-2213-hardening-auth-introspeccao) — o plugin continua validando por introspecção (não por JWKS local), mas o cache não pode exceder `exp` e o usuário é rechecado por requisição. Trade-off: uma query de User por requisição.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2213 | TTL `exp - iat` mantém em cache, depois do vencimento, um token introspectado tarde (2026-11-13).
