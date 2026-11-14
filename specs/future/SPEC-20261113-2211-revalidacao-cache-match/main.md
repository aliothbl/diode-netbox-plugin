# SPEC-20261113-2211: Revalidar acertos do cache de match (`diode:fobj:*`)

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:11
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** find_existing_object, cache, diode:fobj, redis, rename-back, stale-match, invalidate_find_obj_entry, reverse-index, find_obj_cache_ttl
**Features:** differ-matcher
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** alto · **Complexidade:** média
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-2)
**Resumo:** Um acerto no cache Redis de `find_existing_object` só confere se o PK ainda existe. Um objeto renomeado ou alterado fora do Diode continua sendo "achado" pela chave antiga por até `find_obj_cache_ttl`, e o diff seguinte reverte a edição. Esta SPEC passa a revalidar os critérios do matcher sobre a linha em cache e corrige o índice reverso, que hoje guarda uma única chave por PK.

## Objetivo

O cache precisa ser só um atalho de performance, nunca uma fonte de verdade. Um acerto de cache deve dar exatamente a mesma resposta que o loop de matchers daria, ou cair no loop.

## Escopo

**DENTRO:**
- `find_existing_object` (`netbox_diode_plugin/api/matcher.py:2844`). Em um acerto de cache, hoje (`matcher.py:2883-2891`) o código faz `model_class.objects.filter(pk=cached_id).first()` e aceita qualquer linha existente. Passa a:
  1. guardar no cache **qual matcher** produziu o match (nome/índice estável do matcher em `get_model_matchers`), junto com o PK;
  2. no acerto, executar `matcher.build_queryset(data).filter(pk=cached_id).first()`. Se vier `None`, apagar a chave e cair no loop completo.
  Isso custa uma query por acerto (a mesma de antes, só que mais restrita), sem regressão no número de queries.
- **Índice reverso** (`_find_obj_rev_key`, set em `matcher.py:2923-2924`): hoje é um único valor por PK, sobrescrito, e as chaves anteriores ficam órfãs e impossíveis de invalidar. Passa a ser um conjunto (Redis SET via `django_cache` não é portátil, então usar uma lista serializada com teto, ou chave versionada por PK: `diode:fobj:ver:<type>:<pk>` embutida no valor da chave principal). **Decisão:** versão por PK. A chave principal guarda `(pk, matcher_id, ver)` e a invalidação só incrementa `ver`, invalidando todas as chaves daquele PK de uma vez.
- `invalidate_find_obj_entry` (`matcher.py:76`) passa a incrementar a versão do PK.
- **Invalidação por escrita de qualquer origem:** conectar `post_save`/`post_delete` genéricos, filtrados pelos modelos de `_LEGAL_FIELDS`, para incrementar a versão. Hoje só o applier do Diode invalida (`applier.py:1364`), e edições pela UI/API REST do NetBox não. Com a revalidação do item anterior isso vira defesa em profundidade, e o custo é medido (um `cache.incr` por save).
- Teste: renomear um objeto via ORM/API do NetBox entre dois planos → o segundo plano não emite rename-back (deve produzir CREATE ou no-match conforme o matcher).

**FORA:**
- Mudar `non_cacheable_types` (`matcher.py:2812-2817`). A lista atual é justificada no próprio código.
- Cache por requisição (`req_cache`): é por requisição, sem problema de staleness entre requisições.
- TTL padrão (`find_obj_cache_ttl=30`): mantido.

## Invariantes
- SEMPRE: o resultado de `find_existing_object` com cache = o resultado sem cache, para o mesmo estado do banco.
- NUNCA uma falha do cache (Redis fora) pode falhar o plano. Cair no loop de matchers.

## Implementação

1. Introduzir um identificador estável de matcher (`f"{type(m).__name__}:{idx}"` na lista de `get_model_matchers(model_class)`).
2. Valor do cache: `{"pk": id, "m": matcher_id, "v": ver}`. Leitura compatível com o valor legado (int puro) tratada como **miss**.
3. `ver` lido de `diode:fobj:ver:<object_type>:<pk>` (default 0). Mismatch é tratado como miss.
4. Signal handler genérico registrado em `ready()` do plugin, com filtro de modelo por `ContentType` presente em `_LEGAL_FIELDS`.
5. Métricas de profile existentes (`ctx.increment("find_obj_cache_hit")`) ganham `find_obj_cache_revalidation_miss`.

### Modelo de dados
Sem migration. Muda o formato do valor no Django cache (Redis). Chaves legadas são ignoradas e expiram pelo TTL.

<!-- Alternativas:
- Só invalidação por signal (sem revalidar): rejeitada, porque signals não cobrem `QuerySet.update()`, SQL direto nem outra instância/worker antes do incr propagar.
- Desligar o cache Redis: rejeitada, porque o ganho de performance em bulk é o motivo de ele existir. A revalidação preserva a maior parte do ganho.
-->

## Riscos
- Uma query a mais por acerto de cache em matchers caros. Mitigação: `filter(pk=...)` restringe a uma linha e o índice PK domina o plano. Medir com o profile do plugin em um bulk de referência.
- Signal genérico de post_save em todos os modelos legais adiciona custo em escritas fora do Diode. Mitigação: um `cache.incr` (O(1)) e flag de config `find_obj_cache_invalidate_on_any_save` (default true) para desligar.
- `cache.incr` em chave inexistente levanta `ValueError` no Django. Mitigação: `cache.add(key, 0)` antes, ou try/except.

## Sinais de sucesso
- Zero ocorrências de "rename-back" (o Diode desfazendo uma edição humana recente) atribuíveis a cache. Taxa de acerto de cache praticamente igual à anterior.

## Critério de aceite
- [ ] Objeto renomeado fora do Diode não é casado pela chave antiga (sem rename-back) | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k FindObjCacheRevalidation" docker-compose-netbox-plugin-test`
- [ ] Valor legado (int) no cache é tratado como miss, sem erro | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k FindObjCacheLegacy" docker-compose-netbox-plugin-test`
- [ ] Invalidação por PK derruba todas as chaves daquele objeto (versão) | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k FindObjCacheVersion" docker-compose-netbox-plugin-test`
- [ ] Redis indisponível → plano funciona via loop de matchers | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k FindObjCacheDown" docker-compose-netbox-plugin-test`
- [ ] Suíte completa verde na matriz | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v docker-compose-netbox-plugin-test || exit 1; done`
- [ ] Contagem de queries de um bulk-plan de referência ≤ a anterior + 0 por acerto | evidence: manual @aliothbl
