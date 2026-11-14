# SPEC-20261113-2215: Robustez dos endpoints e efeitos do bypass de change logging

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:15
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** generate-diff, object_type, traceback.print_exc, logger.exception, requests-timeout, entities-limit, 413, apply_bypass_change_logging, event-rules, webhooks, enqueue_event
**Features:** api-endpoints
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** médio · **Complexidade:** baixa
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achados P-6 e P-9)
**Resumo:** Pacote de correções de baixo custo:
- `object_type` malformado gera 500;
- `traceback.print_exc()` imprime direto no stdout;
- chamadas `requests` da UI rodam sem timeout;
- lotes de entidades não têm limite;
- há código morto no differ;
- `apply_bypass_change_logging` suprime **também event rules e webhooks** sem que isso esteja documentado (confirmado no código).

## Objetivo

Eliminar 500s evitáveis e workers da UI travados, limitar o tamanho de lote e deixar explícito, com teste, que o bypass de change logging silencia webhooks e event rules.

## Escopo

**DENTRO:**
- **`GenerateDiffView._post`** (`netbox_diode_plugin/api/views.py:325`): `app_label, model_name = object_type.split(".")` sem tratamento. Um valor sem ponto ou com dois pontos gera `ValueError` e 500. Reusar `_extract_entity_data` (já usado nos endpoints bulk) ou validar e retornar 400.
- **`traceback.print_exc()`** em `api/views.py:298-299` (e nos demais handlers com o mesmo padrão em `views.py`) e em `api/applier.py:75-76`: trocar por `logger.exception(...)`. Em `applier.py:77-78`, o log atual inclui o `data` inteiro da entidade. Reduzir para `object_type` e as chaves.
- **Timeouts** em `netbox_diode_plugin/diode/clients.py:92`, `:115`, `:140`, `:166` e `:205` (`requests.post/get/delete` sem `timeout=`). Adicionar `timeout=(5, 30)` configurável. Em `api/authentication.py` já existe `timeout=5`.
- **Limite de lote:** setting `max_entities_per_request` (default 1000, alinhado ao `max_items:1000` do proto de ingestão). Acima do limite, os endpoints bulk retornam **413**.
- **Código morto** em `api/differ.py:202-204`: `str(...)` nunca é `None`. Trocar por `primary_value = get_primary_value(...)` e `str(primary_value) if primary_value is not None else "(unnamed)"`.
- **Bypass de change logging e eventos (fato confirmado):** o handler substituído pelo bypass é `core.signals.handle_changed_object`. No checkout local do NetBox (`/home/alatour/repositories/netbox/netbox`, commit `6ce3012f9`, de 2025-08-05) esse handler também chama `enqueue_event(queue, instance, request.user, request.id, event_type)` (`core/signals.py:105-108`). O próprio `api/change_log_buffer.py:266` registra: *"bypass wins: no ObjectChange row, no buffered entry, no event"*. Portanto, com `apply_bypass_change_logging=True`, **event rules e webhooks não disparam** para CREATE/UPDATE feitos pelo Diode. Entregas:
  - docstring de `api/change_log_bypass.py` e comentário em `__init__.py` (`default_settings`, bloco de `apply_bypass_change_logging`) atualizados;
  - README com aviso;
  - teste que cria uma EventRule e verifica que, com bypass, nenhum evento é enfileirado e, com buffer (`apply_buffer_change_logging`), o evento é enfileirado.
  - Revalidar contra NetBox 4.4–4.7 na ativação, porque o checkout local é anterior a 4.4.

**FORA:**
- Re-enfileirar eventos no modo bypass: mudaria o propósito do bypass. Quem precisa de eventos usa o buffer.

## Invariantes
- NUNCA um erro de input do cliente produz 500.
- SEMPRE toda chamada HTTP de saída do plugin tem timeout.

## Implementação
Ver Escopo. São mudanças pontuais. Cada item vem com teste na árvore de testes.

### Modelo de dados
—

<!-- Alternativas: limite de lote só no server (reconciler) — rejeitada; o plugin é endpoint público de API e precisa se defender sozinho. -->

## Riscos
- O limite de 1000 pode recusar lotes legítimos de clientes manuais. Mitigação: o valor é configurável e o reconciler já usa batch de 100.
- A semântica de eventos pode diferir entre versões do NetBox. Mitigação: o teste roda na matriz.

## Sinais de sucesso
- Zero 500s por input malformado nos logs. A documentação de deploy deixa explícita a troca bypass × eventos.

## Critério de aceite
- [ ] `generate-diff` com `object_type` malformado → 400 ← specctl check
- [ ] Nenhum `traceback.print_exc` restante em `netbox_diode_plugin/` (fora de testes) ← specctl check
- [ ] Todas as chamadas em `diode/clients.py` com `timeout` ← specctl check
- [ ] Lote acima de `max_entities_per_request` → 413 ← specctl check
- [ ] Teste prova: bypass ⇒ sem evento; buffer ⇒ evento; docs atualizadas ← specctl check
- [ ] Fallback `(unnamed)` do differ funcional (teste) ← specctl check
