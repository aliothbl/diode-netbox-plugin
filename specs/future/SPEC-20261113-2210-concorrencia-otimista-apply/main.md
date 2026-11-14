# SPEC-20261113-2210: Concorrência otimista no apply (sem lost update entre plano e aplicação)

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:10
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** lost-update, optimistic-locking, select_for_update, before, changed_attrs, 409, conflict, apply-change-set, bulk-apply, bulk-plan-apply, idempotency
**Features:** applier, differ-matcher
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** `diode/specs/programs/diode-stack-hardening.md`
**Relacionadas:** `diode/specs/future/SPEC-20261113-2145-retry-seguro-apply-plugin/main.md` (consumidora do contrato 409 definido aqui)
**Impacto:** alto · **Complexidade:** média
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-1)
**Resumo:** O UPDATE aplica o pós-change **inteiro**, montado a partir de um snapshot antigo, sem conferir se a linha mudou desde o plano. Esta SPEC passa a gravar só os atributos alterados, compara o `before` sob `select_for_update` e devolve **409 com erro estruturado** quando há divergência. Esse é o contrato que o reconciler vai consumir.

## Objetivo

Hoje uma edição feita no NetBox pela UI ou por outro cliente entre o `bulk-plan` e o `apply-change-set`/`bulk-apply` é sobrescrita em silêncio. No `bulk-plan-apply` a janela é menor, mas existe. O objetivo é que o apply **detecte** a divergência e recuse a mudança daquela entidade de forma explícita e tratável pelo reconciler, sem afetar as demais entidades do lote.

## Escopo

**DENTRO:**
- **Differ:** `diff_to_change` (`netbox_diode_plugin/api/differ.py:191-238`) passa a emitir, para UPDATE, também o subconjunto `changed_attrs`, que já é calculado em `_generate_changeset` (`differ.py:302`). Hoje esse subconjunto só decide UPDATE vs NOOP (`differ.py:200`) e `change.data` recebe o pós-change completo (`differ.py:226-227`, junto com `_partially_merge` em `:295` e `:333-353`). Novo campo opcional em `Change` (`api/common.py:109-120`): `changed_attrs: list[str] | None`.
- **Applier:** no ramo UPDATE com `object_id` (`api/applier.py:1357-1364`):
  1. Trocar `model_class.objects.get(id=object_id)` por `select_for_update().get(...)`. O apply já roda dentro de `transaction.atomic()` por entidade (`api/views.py`, `_apply_one_changeset` e `BulkPlanApplyView`).
  2. Recalcular `prechange_data_from_instance(instance)` (`differ.py:51`) e comparar **somente** as chaves de `changed_attrs` contra `change.before`, com a mesma normalização do differ (`_tidy`, `canonical.py`).
  3. Se houver divergência, lançar `ChangeSetConflict` e **não** salvar.
  4. Se não houver, chamar `serializer_class(instance, data=<data filtrado por changed_attrs + chaves obrigatórias de merge>, partial=True)`.
- **Contrato HTTP de conflito** (consumido pelo diode server):
  - Status **409**. Corpo no formato atual de `ChangeSetResult.errors`: `{"<object_type>": {"__conflict__": ["<campo>: esperado <before>, atual <valor>"]}}`, mais `"conflict": true` no nível do resultado da entidade nos endpoints bulk.
  - Nos bulk (`bulk-apply`, `bulk-plan-apply`), o conflito é **por entidade**: as demais seguem e o resultado da entidade carrega `status_code: 409`.
- **Compatibilidade:** se `changed_attrs` vier ausente (reconciler antigo), o comportamento atual se mantém (apply do `data` completo, sem checagem) e o plugin loga `deprecated: change without changed_attrs`.
- **`custom_fields` e `tags`:** `_partially_merge` mescla `custom_fields` e `tags` a partir do prechange. A checagem compara só as chaves de CF presentes no payload do produtor e, em `tags`, o conjunto final esperado.
- Testes na árvore de cada versão suportada (ou na árvore unificada, se a SPEC-20261113-2217 vier antes):
  - UPDATE concorrente simulado entre plano e apply → 409.
  - Edição concorrente em campo **não** tocado pelo plano → apply OK, sem sobrescrever o campo alheio.
  - Payload sem `changed_attrs` → comportamento legado.

**FORA:**
- Lado do diode server: retry/estado "conflict" no reconciler. Fica com a SPEC-20261113-2145 do repo `diode`.
- Concorrência em CREATE: já coberta por `_create_or_find_instance` (`applier.py:1193`) com fallback em IntegrityError.
- Lock pessimista durante o plano (bloquear linhas entre plan e apply): rejeitado (ver Alternativas).

## Invariantes
- NUNCA gravar em um campo que o produtor não pediu para mudar (`changed_attrs`), exceto nas chaves de merge obrigatórias documentadas no código.
- SEMPRE decidir o conflito dentro da mesma transação que grava (`select_for_update` antes de comparar).
- NUNCA um conflito de uma entidade pode abortar as outras entidades do mesmo lote bulk.

## Implementação

Ordem: differ (emite `changed_attrs`) → `Change` serializa/deserializa o campo (`common.py:122` `to_dict`, e o parse em `views.py`) → applier (lock + comparação + filtro) → views (mapear `ChangeSetConflict` → 409 por entidade) → testes.

Comparação: reutilizar o caminho de normalização do differ (`shallow_compare_dict` em `_generate_changeset`), para que "igual" no plano e "igual" no apply signifiquem a mesma coisa. Não comparar `last_updated`: ele muda com efeitos colaterais de signals do próprio NetBox (counters, VC master, ver comentário em `applier.py:1369-1380`) e daria falso-positivo.

**Decisão sobre idempotência:** fica como **pergunta aberta** (ver Riscos). Esta SPEC não introduz `Idempotency-Key`. Com a checagem de `before`, um reenvio do mesmo UPDATE depois do primeiro ter sido aplicado vira 409 ("atual" = valor novo ≠ `before`). O reconciler pode tratar isso como "já aplicado" comparando `atual` com `data`. Por isso o corpo do 409 traz `expected` (before), `actual` e `desired` (data) por campo.

### Modelo de dados
Sem migration. Muda o payload de `Change`: novo campo opcional `changed_attrs` (lista de strings). O corpo do 409 é novo e está documentado acima.

<!-- Alternativas:
- Comparar `last_updated` (versão por timestamp): rejeitada, porque signals do NetBox alteram a linha sem mudança semântica e o resultado seria 409 espúrio.
- Lock pessimista no plano (`select_for_update` no bulk-plan): rejeitada. O plano e o apply são requisições separadas e o lock não sobrevive ao fim da transação.
- Last-write-wins documentado: rejeitada. É o comportamento atual e o achado é exatamente que ele perde edições humanas.
-->

## Riscos
- **Pergunta aberta: idempotência.** Mapear o 409 "actual == desired" como sucesso no reconciler é suficiente, ou é preciso `Idempotency-Key` com tabela de deduplicação no plugin? A decisão fica para a ativação desta SPEC em conjunto com a SPEC-20261113-2145. Mitigação: o corpo do 409 já traz `actual`/`desired` para permitir a primeira opção.
- Normalização divergente entre differ e applier (ex.: ordem de listas, decimal vs string) gera 409 falso. Mitigação: usar exatamente as mesmas funções de normalização e cobrir com teste de round-trip plano→apply sem concorrência (zero 409).
- `select_for_update` aumenta a contenção e o risco de deadlock em bulk. Mitigação: o retry de deadlock 40P01 já existe em `views.py` (comentário em `:62` e `:169-185`). Medir com `profile.py` antes e depois.
- Reconciler antigo sem `changed_attrs` continua sem proteção. Mitigação: log de depreciação e métrica, e coordenar com a SPEC do server.

## Sinais de sucesso
- Uma edição feita pela UI entre plan e apply deixa de ser revertida. Em produção, aparecem 409s raros e rastreáveis em vez de sobrescritas silenciosas.

## Critério de aceite
- [ ] `Change` serializa/deserializa `changed_attrs` e o differ o preenche em UPDATE | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k ChangedAttrs" docker-compose-netbox-plugin-test`
- [ ] UPDATE concorrente em campo planejado → 409 com `expected/actual/desired`, sem escrita | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k ApplyConflict" docker-compose-netbox-plugin-test`
- [ ] Edição concorrente em campo NÃO planejado → apply OK e o campo alheio preservado | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k ApplyConflict" docker-compose-netbox-plugin-test`
- [ ] Em bulk, um conflito afeta só a própria entidade (as demais → 200) | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k BulkConflict" docker-compose-netbox-plugin-test`
- [ ] Payload sem `changed_attrs` mantém o comportamento legado | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k LegacyChange" docker-compose-netbox-plugin-test`
- [ ] Suíte completa verde nas 4 versões da matriz | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v docker-compose-netbox-plugin-test || exit 1; done`
- [ ] Contrato 409 documentado no README e acordado com a SPEC-20261113-2145 (diode) | evidence: manual @aliothbl
