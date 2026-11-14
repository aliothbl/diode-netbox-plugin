# SPEC-20261113-2214: Allowlist de tipos graváveis (schema e links de UI ficam match-only)

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:14
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** MATCH_ONLY_TYPES, _LEGAL_FIELDS, extras.customfield, extras.customlink, core.managedfile, users.owner, netbox:write, ObjectPermission, restrict, least-privilege
**Features:** applier, api-auth
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** médio · **Complexidade:** média
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-5)
**Resumo:** Qualquer token com `netbox:write` pode criar ou alterar `extras.customfield` (schema), `extras.customlink` (links na UI), `core.managedfile` e `users.owner` via `apply-change-set`. Só `users.user` é match-only. Esta SPEC torna esses tipos match-only por padrão, com opt-in por configuração, e restringe as escritas pelas ObjectPermissions do usuário diode.

## Objetivo

Reduzir o raio de impacto de um token de ingestão vazado ou de um produtor com bug: ingerir inventário não deve permitir alterar o schema do NetBox nem injetar links/HTML na UI.

## Escopo

**DENTRO:**
- `MATCH_ONLY_TYPES` (`netbox_diode_plugin/api/common.py:39`, hoje `frozenset({"users.user"})`) passa a ser `DEFAULT_MATCH_ONLY_TYPES | set(config.match_only_types) - set(config.writable_overrides)`, com default `{"users.user", "users.owner", "extras.customfield", "extras.customlink", "core.managedfile"}`. Os quatro tipos novos estão presentes em `_LEGAL_FIELDS` (`api/plugin_utils.py:3277`, gerado do NetBox 4.7.0), confirmado na leitura.
- O applier já trata match-only (`api/applier.py`, ramo `if change.object_type in MATCH_ONLY_TYPES and change_type in (CREATE, UPDATE)`, em `_apply_change`). Garantir erro **por entidade** (`_err(...)`) com mensagem `"<type> is match-only in this deployment"`.
- `_validate_change_set` (`applier.py:1493-1503`) passa a rejeitar `object_type` fora de `_LEGAL_FIELDS`. Hoje um tipo desconhecido só falha mais adiante, em `get_object_type_model`.
- **Permissões de objeto (opt-in, default off nesta SPEC):** setting `apply_enforce_object_permissions`. Quando ligado, CREATE/UPDATE passam por `model_class.objects.restrict(request.user, "add"|"change")`. As permissões provisionadas hoje (`provisioning.py`: view em todos os tipos e add em `dcim.macaddress`) seriam insuficientes, então provisionar um conjunto padrão (add/change nos tipos não match-only) na migração `post_migrate`.
- Documentação no README: a tabela de tipos match-only e como liberar.

**FORA:**
- Tornar `extras.tag` match-only. É um tipo de uso legítimo e frequente pelos produtores.
- Mudar escopos OAuth (`netbox:write` granular por tipo). Ficaria no auth server.

## Invariantes
- NUNCA um deployment com configuração padrão permite que o Diode crie ou altere custom fields, custom links, managed files ou owners.
- SEMPRE a recusa é por entidade: um tipo bloqueado não derruba o lote inteiro.

## Implementação
1. Settings novas em `__init__.py` (`default_settings`): `match_only_types: []` e `writable_overrides: []`.
2. Função `get_match_only_types()` com `lru_cache` invalidado no reload de config, usada no applier e no transformer (para que o plano já marque NOOP/erro e não CREATE).
3. Teste de cada tipo bloqueado via `apply-change-set` → erro por entidade. Teste de override liberando `extras.customfield`.
4. Fase 2 (mesma SPEC, flag off por padrão): `restrict()` mais provisionamento de permissões.

### Modelo de dados
Sem migration de schema. A migração de dados opcional (fase 2) cria ObjectPermissions padrão para o usuário diode.

<!-- Alternativas:
- Bloquear via escopo OAuth: rejeitada, porque exige mudança cross-repo (auth server e SDK) para um benefício que o plugin consegue entregar sozinho.
- Ligar `restrict()` por padrão: rejeitada nesta SPEC, por quebrar instalações existentes sem permissões provisionadas. Fica opt-in, com plano de tornar default numa major.
-->

## Riscos
- Produtores que hoje criam custom fields via Diode (ex.: agentes que publicam CF próprios) quebram. Mitigação: `writable_overrides` e nota de breaking change no CHANGELOG. Checar os produtores internos antes do deploy.
- `restrict()` pode negar escritas legítimas quando as permissões estão incompletas. Mitigação: opt-in, com provisionamento automático.

## Sinais de sucesso
- Um token `netbox:write` não consegue alterar o schema do NetBox na configuração padrão. Nenhuma regressão na ingestão de inventário.

## Critério de aceite
- [ ] Cada tipo padrão match-only recusado por entidade em `apply-change-set` e `bulk-plan-apply` | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k MatchOnlyTypes" docker-compose-netbox-plugin-test`
- [ ] `writable_overrides` reabilita o tipo | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k MatchOnlyOverride" docker-compose-netbox-plugin-test`
- [ ] `object_type` fora de `_LEGAL_FIELDS` → erro de validação claro | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k ValidateChangeSet" docker-compose-netbox-plugin-test`
- [ ] Com `apply_enforce_object_permissions=True`, escrita sem permissão → erro por entidade | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k EnforceObjectPermissions" docker-compose-netbox-plugin-test`
- [ ] Suíte completa verde na matriz | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v docker-compose-netbox-plugin-test || exit 1; done`
- [ ] README documenta tipos match-only e overrides | evidence: manual @aliothbl
