# Feature: branching

**Keywords:** netbox-branching, X-NetBox-Branch, Setting.branch, default-branch, schema_id, active_branch
**Arquivos principais:**
  - netbox_diode_plugin/api/views.py
  - netbox_diode_plugin/models.py
**Resumo:** Integração opcional com netbox-branching: o reconciler envia X-NetBox-Branch, o middleware do branching ativa a branch e o plugin anota o resultado.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2212-branch-coerente-sem-header | 400 sem header quando há branch padrão; 1 Branch.get por requisição | anotação diverge da escrita

## Estado atual

`_get_branch_schema_id` (`views.py:197-215`) usa o header ou, na falta dele, `Setting.branch.schema_id`. No fallback a branch **não** está ativa (só o middleware ativa, por header, `_branch` ou cookie), então os dados vão para main enquanto o resultado é anotado com a branch. `_add_branch_to_result` (`:218`) faz `Branch.objects.get` por entidade. `Setting.branch` (`models.py:54`) consulta a cada acesso e engole exceções. O server envia o header (`client.go:346,440`) e faz fail-closed com cache frio (diode#586).

## Decisões arquiteturais ativas
- DEC-20261113-2156-sem-header-com-branch-e-400 [ativa] (SPEC-20261113-2212-branch-coerente-sem-header) — a falta do header com branch padrão configurada é erro de cliente (400); o plugin não ativa branch por conta própria. Trade-off: chamadas manuais antigas quebram.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2212 | resultado anotado com a branch X enquanto a escrita ocorreu em main quando falta o header (2026-11-13).
