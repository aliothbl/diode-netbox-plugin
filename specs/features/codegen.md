# Feature: codegen

**Keywords:** generated-code, plugin_utils, _LEGAL_FIELDS, RefInfo, ingester.proto, server_utils.go, netbox-schema
**Arquivos principais:**
  - netbox_diode_plugin/api/plugin_utils.py
  - netbox_diode_plugin/api/compat.py
  - netbox_diode_plugin/api/supported_models.py
**Resumo:** Código gerado a partir do schema do NetBox (v4.7.0) que define os tipos/campos legais e as referências usadas pelo transformer, matcher e applier.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2218-gerador-plugin-utils-versionado | Check de drift + regeneração reproduzível | gerador ausente dos repos

## Estado atual

`api/plugin_utils.py` (5.022 linhas, `_LEGAL_FIELDS` em `:3277`) tem cabeçalho "Generated code. DO NOT EDIT. Source: NetBox v4.7.0, Timestamp 2026-09-02 20:52:39Z". A mesma execução gerou `diode-proto/diode/v1/ingester.proto` (20:52:37Z), `diode-server/gen/netbox/server_utils.go` e o `ingester.py` do SDK (20:52:38Z). O gerador não está em nenhum dos três repositórios. A compatibilidade com 4.4–4.6 vem de `compat.py`/`supported_models.py` em runtime.

## Decisões arquiteturais ativas
- DEC-20261113-2159-plugin-utils-vendored [ativa] (SPEC-20261113-2218-gerador-plugin-utils-versionado) — enquanto o gerador não for público, `plugin_utils.py` é tratado como vendored: só muda por sync, e um teste de consistência garante coerência com os modelos e com o proto. Trade-off: não regeneramos sozinhos.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2218 | `plugin_utils.py` é gerado do NetBox 4.7.0 e atende 4.4–4.7. Campos ausentes em versões antigas dependem de `compat.py` (2026-11-13).
