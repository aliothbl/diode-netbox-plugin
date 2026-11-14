# Feature: differ-matcher

**Keywords:** differ, matcher, find_existing_object, diode:fobj, cache, changed_attrs, _partially_merge, customfield-cache
**Arquivos principais:**
  - netbox_diode_plugin/api/differ.py
  - netbox_diode_plugin/api/matcher.py
  - netbox_diode_plugin/api/transformer.py
  - netbox_diode_plugin/api/customfield_cache.py
**Resumo:** Cálculo do plano: o transformer achata a entidade, o matcher acha objetos existentes (com cache por requisição e Redis) e o differ gera Change CREATE/UPDATE/NOOP.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2210-concorrencia-otimista-apply | Emitir changed_attrs e permitir checagem de before | lost update
- SPEC-20261113-2211-revalidacao-cache-match | Revalidar acertos de diode:fobj:* | rename-back por cache stale
- SPEC-20261113-2132-sync-upstream-develop-2026-11 | #219/#222 invalidação de CF entre workers, #227 tags_resolved | sync

## Estado atual

`generate_changeset` (`differ.py:251`) compara o snapshot (`prechange_data_from_instance`, `:51`) com a entidade mesclada (`_partially_merge`, `:333`, que mescla `tags` e `custom_fields` a partir do prechange). `changed_attrs` é calculado (`:302`), mas só decide UPDATE vs NOOP: `change.data` leva o pós-change completo (`:226-227`). `find_existing_object` (`matcher.py:2844`) usa um cache por requisição e um cache Django/Redis `diode:fobj:<sha>` (TTL `find_obj_cache_ttl`=30) com índice reverso de valor único por PK. Um acerto só checa `filter(pk=...)` (`:2883-2891`). Os tipos `dcim.cable`, `dcim.rack`, `dcim.rackreservation` e `dcim.virtualchassis` não são cacheáveis (`:2812-2817`). Os caches de CustomField são `lru_cache` por processo, invalidados por signal local. O upstream #219 já resolveu isso com um token de versão no cache (`customfield_version.py`).

## Decisões arquiteturais ativas
- DEC-20261113-2152-cache-match-so-atalho [ativa] (SPEC-20261113-2211-revalidacao-cache-match) — o cache de match é otimização e nunca fonte de verdade: um acerto deve revalidar os critérios do matcher. Trade-off: uma query restrita por acerto.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2211 | o acerto do cache Redis aceita qualquer linha com o PK, então um objeto renomeado pela UI volta ao nome antigo no próximo plano em até 30 s (2026-11-13).
- SPEC-20261113-2210 | `primary_value = str(...)` nunca é None: o fallback `(unnamed)` em `differ.py:202-204` é código morto (corrigido na SPEC-20261113-2215).
