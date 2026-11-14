# SPEC-20261113-2218: `plugin_utils.py` reproduzível e verificável (gerador versionado ou check de drift)

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:18
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** codegen, plugin_utils, _LEGAL_FIELDS, RefInfo, generated-code, drift, netbox-schema, ingester.proto, server_utils.go, reproducibility
**Features:** codegen
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Relacionadas:** `diode-sdk-python/specs/future/SPEC-20261113-2208-verificacao-drift-codegen/main.md` (mesmo gerador, lado SDK)
**Impacto:** médio · **Complexidade:** média
**Estratégia upstream:** upstream-first. Pedir à NetBox Labs (issue em netboxlabs/diode-netbox-plugin) a publicação do gerador ou ao menos do comando que o invoca. Enquanto isso não acontece, o check de drift (fase 1) não depende do gerador e pode ir como PR.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-11)
**Resumo:** `api/plugin_utils.py` (5.022 linhas, cabeçalho "Generated code. DO NOT EDIT. Source: NetBox v4.7.0") é gerado por uma ferramenta que **não está em nenhum dos três repositórios**. Ele saiu da mesma execução que gerou `diode-proto/diode/v1/ingester.proto`, `diode-server/gen/netbox/server_utils.go` e o `ingester.py` do SDK (timestamps de 2026-09-02 20:52:37–39Z). Esta SPEC adiciona um check de consistência no CI e a regeneração versionada.

## Objetivo

Hoje não dá para regenerar nem auditar o arquivo do qual dependem matcher, transformer e applier, e um ajuste manual ou uma atualização parcial passaria despercebida. O objetivo é ter (1) um teste que prove a coerência de `plugin_utils.py` com os modelos do NetBox em execução e com o `ingester.proto`, e (2) um caminho reproduzível de regeneração.

## Escopo

**DENTRO:**
- **Fase 1: check de drift sem o gerador.** Teste na suíte que, dentro do container NetBox de cada versão da matriz:
  - Para cada `object_type` em `_LEGAL_FIELDS` (`api/plugin_utils.py:3277`), confirma que o modelo existe (`apps.get_model`) **ou** que ele está listado em `api/supported_models.py`/`compat.py` como ausente naquela versão.
  - Para cada campo legal, confirma que existe no modelo (ou é um acessor genérico conhecido), também tolerando as exceções declaradas em `compat.py`.
  - Compara o conjunto de tipos de `_LEGAL_FIELDS` com o conjunto de mensagens de `Entity` no `ingester.proto` do server (fixture com a lista extraída, atualizada pelo sync).
  - Falha com uma lista legível de divergências.
- **Fase 2: regeneração versionada.** Depende da resposta do upstream:
  - Se o gerador for publicado: `make generate` invocando-o, mais um job de CI que regenera e falha com `git diff --exit-code`.
  - Se não for: documentar em `specs/features/codegen.md` que o arquivo é tratado como **vendored** e só muda por sync com o upstream. O check da fase 1 vira a garantia.
- Cabeçalho: o teste lê `# Source: NetBox vX` e avisa (sem falhar) quando a versão máxima da matriz é maior que a do cabeçalho.

**FORA:**
- Escrever um gerador próprio: duplicaria a ferramenta da NetBox Labs e divergiria a cada release.
- Mudanças de comportamento no matcher/transformer.

## Invariantes
- NUNCA editar `plugin_utils.py` à mão no fork. Ele só muda via sync com o upstream ou pelo gerador oficial.
- SEMPRE o check de drift roda na matriz inteira de versões.

## Implementação
1. `tests/test_plugin_utils_consistency.py` (na árvore unificada, se a SPEC-20261113-2217 tiver sido feita; senão, nas 4 árvores).
2. Fixture `tests/fixtures/ingester_entities.txt`, gerada por script a partir de `diode/diode-proto/diode/v1/ingester.proto` (lista de campos do `oneof entity`) e atualizada no sync.
3. Issue upstream pedindo o gerador, com o link registrado no journal na ativação.

### Modelo de dados
—

<!-- Alternativas: introspecção dos modelos em runtime para substituir `_LEGAL_FIELDS` — rejeitada; mudaria comportamento (campos novos do NetBox passariam a ser graváveis sem decisão) e custaria tempo de startup. -->

## Riscos
- Falsos positivos em campos legais derivados (properties, GenericForeignKey). Mitigação: allowlist explícita no teste, com comentário do porquê de cada entrada.
- O upstream não publicar o gerador. Mitigação: a fase 1 entrega o valor principal sozinha.

## Sinais de sucesso
- Uma atualização de NetBox que remove ou renomeia um campo gera falha de teste nomeando o campo, em vez de erro em produção.

## Critério de aceite
- [ ] Teste de consistência `_LEGAL_FIELDS` × modelos verde na matriz | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v TEST_FLAGS="-k PluginUtilsConsistency" docker-compose-netbox-plugin-test || exit 1; done`
- [ ] Teste de consistência `_LEGAL_FIELDS` × `ingester.proto` verde | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k PluginUtilsProto" docker-compose-netbox-plugin-test`
- [ ] Remover um campo de `_LEGAL_FIELDS` em um branch de teste faz o check falhar com mensagem legível | evidence: manual @aliothbl
- [ ] Issue upstream aberta e decisão da fase 2 registrada | evidence: manual @aliothbl
