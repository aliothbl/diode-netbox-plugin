# SPEC-20261113-2213: Endurecer a autenticação por introspecção (TTL, usuário inativo, `aud`)

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:13
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** oauth2, introspection, rfc7662, token-cache, exp, iat, aud, is_active, kill-switch, DiodeOAuth2Authentication
**Features:** api-auth
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** médio · **Complexidade:** baixa
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-4)
**Resumo:** Três defeitos na autenticação:
- o cache do token usa `exp - iat` como TTL, o que aceita tokens já vencidos;
- o `User` em cache não é rechecado quanto a `is_active`, o que impede revogar o acesso desativando o usuário;
- `aud` em formato string vira um conjunto de caracteres.

## Objetivo

Garantir que a autenticação nunca aceite um token depois do seu `exp`, que desativar o usuário de serviço do Diode corte o acesso em segundos e que um `aud` válido segundo o RFC 7662 seja interpretado corretamente.

## Escopo

**DENTRO:**
- `DiodeOAuth2Authentication._introspect_token` (`netbox_diode_plugin/api/authentication.py`):
  - TTL: hoje é `data["exp"] - data["iat"]` (`authentication.py:95-99`), a vida inteira do token contada a partir da emissão. Passa a ser `max(0, min(exp - now, AUTH_CACHE_MAX_TTL))`, com teto configurável (default 300 s). Se `exp - now <= 0`, rejeitar o token sem cachear.
  - `aud`: hoje é `set(data.get("aud", []))` (`authentication.py:83`). Se `aud` for string, o resultado é um conjunto de caracteres. Normalizar: `aud = [aud] if isinstance(aud, str) else (aud or [])`.
  - Cache: guardar só `{user_id, scopes, token_data}`, não o objeto `User` inteiro (`SimpleNamespace(user=get_diode_user(), ...)`, `authentication.py:89-93`). Recarregar o `User` por PK a cada requisição. É uma query, que pode ficar em cache local de 5 s se o profile mostrar impacto.
- `IsAuthenticated` (`api/permissions.py:11-16`): exigir também `request.user.is_active`.
- Testes: token com `exp` a 2 s não é aceito após 3 s, mesmo com cache; usuário diode desativado gera 401/403 na requisição seguinte; `aud` string aceito quando bate com a audiência exigida.

**FORA:**
- Trocar a introspecção por validação JWT local (JWKS). É uma decisão de arquitetura do lado server/auth (ver a SPEC de JWT no repo `diode`).
- Revogação ativa de tokens (o Hydra já responde `active=false` na introspecção seguinte).

## Invariantes
- NUNCA aceitar um token depois de `exp`.
- NUNCA aceitar uma requisição de usuário com `is_active=False`.

## Implementação
Ver Escopo. A mudança fica restrita a `authentication.py`, `permissions.py` e às settings do plugin (`__init__.py` `default_settings`, nova chave `auth_cache_max_ttl`).

### Modelo de dados
— (muda só o formato do valor em cache `diode:oauth2:introspect:<sha256>`. Valores antigos expiram pelo TTL).

<!-- Alternativas: invalidar cache ao desativar o usuário via signal — rejeitada como único mecanismo (não cobre alteração direta no banco); a rechecagem por requisição é simples e barata. -->

## Riscos
- Uma query extra por requisição para carregar o `User`. Mitigação: o custo é desprezível frente ao apply. Se o profile mostrar impacto, usar cache local curto.
- Tokens sem `exp` (configuração atípica do Hydra) ficam com TTL de 300 s, como hoje.

## Sinais de sucesso
- Desativar o usuário diode no NetBox interrompe o apply em ≤ 1 requisição. Nenhum token vencido é aceito.

## Critério de aceite
- [ ] TTL do cache = `min(exp - now, teto)`, e token vencido é rejeitado mesmo com cache ← specctl check
- [ ] Usuário diode inativo → requisição negada ← specctl check
- [ ] `aud` string e `aud` lista tratados corretamente ← specctl check
- [ ] Cache não guarda o objeto `User` ← specctl check
