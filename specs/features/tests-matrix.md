# Feature: tests-matrix

**Keywords:** tests, v4.4.x, v4.5.x, v4.6.x, v4.7.x, matrix, Makefile, TEST_SELECTOR, docker-compose
**Arquivos principais:**
  - netbox_diode_plugin/tests/
  - Makefile
  - docker/
  - .github/workflows/lint-tests.yml
**Resumo:** Suíte de testes Django executada dentro de imagens NetBox por versão (4.4.10, 4.5.5, 4.6.10, 4.7.0), com uma árvore de testes duplicada por versão.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2217-unificar-arvores-de-teste | Árvore única com gates de versão | duplicação e drift

## Estado atual

São 4 árvores (`tests/v4.4.x`…`v4.7.x`) com 43/43/48/46 arquivos e ~89 mil linhas no total, das quais 25 arquivos são idênticos nas 4. `Makefile:21` seleciona a árvore por `NETBOX_MINOR_VERSION` (default `v4.5.5`). Há drift: os testes de rackreservation existem em 4.6 e não em 4.7. O CI roda a matriz, mas o gatilho de push está quebrado (ver packaging-ci).

## Decisões arquiteturais ativas
- DEC-20261113-2157-unificacao-so-com-upstream [ativa] (SPEC-20261113-2217-unificar-arvores-de-teste) — a unificação só é aplicada no fork se o upstream aceitar a RFC; caso contrário, entra apenas um check de drift. Trade-off: o benefício fica condicionado à NetBox Labs.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2217 | cada correção upstream copia o mesmo teste 4× (ex.: #219, 302 linhas × 4) e testes se perdem entre árvores (2026-11-13).
