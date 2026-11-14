# Feature: packaging-ci

**Keywords:** pyproject, setuptools, semantic-release, pypi, trusted-publishing, github-actions, ruff, dependabot
**Arquivos principais:**
  - pyproject.toml
  - .github/workflows/lint-tests.yml
  - .github/workflows/release.yaml
  - docker/v4.*/requirements-diode-netbox-plugin.txt
**Resumo:** Empacotamento (setuptools, versão injetada no build), CI de lint/testes em matriz e release por semantic-release com publicação no PyPI.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2216-ci-dependencias-hardening | Push trigger, release seguro, guarda de fork, deps | testes não rodam em push
- SPEC-20261113-2132-sync-upstream-develop-2026-11 | #223 certifi, #225 sem Brotli | sync

## Estado atual

`lint-tests.yml` usa `push.branches: ["!release"]` (só negativo, o push não dispara) e `contents: write` no workflow. O lint e os testes são agregados em "Check results". `release.yaml` publica sdist no PyPI no job `build` (sem gate de `new-release-published`) **antes** do job que cria a tag, usa `::set-output` e trata `perf*` como major. O `pyproject` declara `grpcio`/`protobuf` (não importados) e omite `requests` (importado). Os requirements do Docker fixam versões que conflitam com o pyproject (v4.4: `grpcio==1.62.1`). Não há Dependabot.

## Decisões arquiteturais ativas
- DEC-20261113-2158-guarda-de-owner-no-release [ativa] (SPEC-20261113-2216-ci-dependencias-hardening) — os jobs de publicação só rodam com `github.repository_owner == 'netboxlabs'`. Trade-off: patch local, se o upstream recusar.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2216 | filtro de push só com padrão negativo faz o GitHub não disparar o workflow; usar `branches-ignore` (2026-11-13).
