# Feature: applier

**Keywords:** applier, apply_changeset, serializer, MATCH_ONLY_TYPES, select_for_update, bound_only, virtualchassis-adoption, transaction
**Arquivos principais:**
  - netbox_diode_plugin/api/applier.py
  - netbox_diode_plugin/api/common.py
  - netbox_diode_plugin/api/views.py
**Resumo:** Aplicação do change set: CREATE/UPDATE via serializers DRF dentro de transaction.atomic por entidade, com pre-save match, bind sem escrita, adoção de VC e refs new_object.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2210-concorrencia-otimista-apply | Lock + comparação de before + 409 | lost update
- SPEC-20261113-2214-allowlist-tipos-gravaveis | Ampliar match-only e restrict() opt-in | superfície de escrita

## Estado atual

`apply_changeset` (`applier.py:44`) itera as mudanças e pula NOOP. `_apply_change` (`:1297`) recusa CREATE/UPDATE em `MATCH_ONLY_TYPES` (hoje só `users.user`, `common.py:39`). No UPDATE com `object_id` (`:1357-1364`), o fluxo é `objects.get` → `snapshot_for_apply` → `serializer(partial=True)` → `save()` → `invalidate_find_obj_entry`, **sem** lock nem comparação com `change.before`. Erros viram `_err(...)` por entidade. `TypeError` ainda usa `traceback.print_exc()` (`:75`). As escritas são feitas pelo usuário de serviço `diode_username`, com ObjectPermissions provisionadas (view em todos os tipos e add em `dcim.macaddress`), mas o serializer não aplica `restrict()`.

## Decisões arquiteturais ativas
- DEC-20261113-2153-conflito-409-por-entidade [ativa] (SPEC-20261113-2210-concorrencia-otimista-apply) — a divergência entre `before` e o estado atual nos `changed_attrs` gera 409 por entidade, com expected/actual/desired; não usar `last_updated` como versão. Trade-off: exige normalização idêntica entre differ e applier.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2210 | signals do NetBox reescrevem linhas durante o apply (ex.: `assign_virtualchassis_master`), por isso `last_updated` não serve como token de versão (2026-11-13).
