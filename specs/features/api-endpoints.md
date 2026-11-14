# Feature: api-endpoints

**Keywords:** generate-diff, bulk-plan, bulk-apply, bulk-plan-apply, apply-change-set, default-branch, deadlock-retry, bypass, buffer
**Arquivos principais:**
  - netbox_diode_plugin/api/views.py
  - netbox_diode_plugin/api/urls.py
  - netbox_diode_plugin/api/change_log_bypass.py
  - netbox_diode_plugin/api/change_log_buffer.py
  - netbox_diode_plugin/diode/clients.py
**Resumo:** Endpoints REST do plugin consumidos pelo reconciler (bulk-plan, bulk-plan-apply, default-branch) e legados (generate-diff, apply-change-set, bulk-apply), mais as otimizações opt-in de side effects.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2215-robustez-endpoints-bypass | 400 em input inválido, timeouts, limite de lote, docs do bypass | 500s e workers travados

## Estado atual

As rotas estão em `api/urls.py:20-25`. O server Go atual chama só `bulk-plan/`, `bulk-plan-apply/` e `default-branch/`. Cada entidade é aplicada em `transaction.atomic()`, com retry em deadlock 40P01. Seis flags opt-in de bypass/buffer ficam em `default_settings` (`__init__.py`). `apply_bypass_change_logging` troca `core.signals.handle_changed_object`, e com isso suprime também `enqueue_event` (event rules/webhooks), comportamento confirmado em `change_log_buffer.py:266` e no `core/signals.py` do NetBox. Os `requests` de `diode/clients.py` rodam sem timeout. Não há limite de tamanho de lote.

## Decisões arquiteturais ativas
- DEC-20261113-2155-bypass-sem-eventos-documentado [ativa] (SPEC-20261113-2215-robustez-endpoints-bypass) — o bypass de change logging continua suprimindo eventos; quem precisa de webhooks usa `apply_buffer_change_logging`. Trade-off: duas flags parecidas com semânticas diferentes, mitigado com documentação e teste.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2215 | `apply_bypass_change_logging=True` silencia webhooks/event rules para escritas do Diode, e a docstring só menciona o audit log (2026-11-13).
