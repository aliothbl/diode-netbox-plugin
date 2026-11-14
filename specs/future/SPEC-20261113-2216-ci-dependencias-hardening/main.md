# SPEC-20261113-2216: CI que roda em push, release seguro, fork sem publicação e dependências corretas

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:16
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** github-actions, branches-ignore, permissions, set-output, semantic-release, perf-major, wheel, pypi, trusted-publishing, dependabot, grpcio, protobuf, requests, pip-check, fork-guard
**Features:** packaging-ci
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** alto · **Complexidade:** baixa
**Estratégia upstream:** upstream-first para as correções genéricas (filtro de push, permissões, `set-output`, wheel, deps), via PR em netboxlabs/diode-netbox-plugin. A **guarda de fork** (não publicar fora de `netboxlabs/*`) também vai upstream como condição `github.repository_owner == 'netboxlabs'`, que não tem efeito no upstream.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achados P-12 e P-13)
**Resumo:** Hoje os testes **não rodam em push** para `develop`, por um filtro de branch só negativo. O release publica no PyPI antes da tag, não tem gate e roda no fork. As dependências declaradas não batem com o código. Esta SPEC corrige o workflow, protege o fork contra publicação e limpa as dependências.

## Objetivo

O CI precisa cobrir o que entra em `develop`, o release precisa ser atômico e seguro, e nosso fork nunca pode publicar pacote, tag ou release sob o nome do upstream.

## Escopo

**DENTRO:**
- **`.github/workflows/lint-tests.yml`:**
  - `push.branches: ["!release"]` (`:10-12`) tem só padrão negativo. O GitHub exige ao menos um padrão positivo junto de negativos, então o gatilho de push não dispara. Trocar por `branches-ignore: [release]`.
  - `permissions` no nível do workflow é `contents: write`, `checks: write` e `pull-requests: write` (`:27-30`). Reduzir para `contents: read` no workflow e conceder `pull-requests: write` só no passo de comentário de cobertura.
  - Fixar a versão do Ruff em `[project.optional-dependencies].dev`.
- **`.github/workflows/release.yaml`:**
  - `echo "::set-output ..."` (`:104`) → `>> "$GITHUB_OUTPUT"`.
  - Regra `{"message": "perf*", "release": "major"}` (`:71`) → `minor` (ou remover). Hoje um commit de performance gera major.
  - Job `build` (`:130-169`) sem `if: needs.get-next-version.outputs.new-release-published == 'true'`. Adicionar o gate.
  - Ordem: hoje o PyPI é publicado no job `build` (`:166-169`) **antes** do job `semantic-release` (`needs: [build]`, `:171-173`), que cria a tag. Reordenar para tag/GitHub release primeiro e publish depois (job `publish` com `needs: [semantic-release]`, `environment: pypi`).
  - Gerar wheel além do sdist: `python3 -m build --outdir dist/` em vez de `--sdist` (`:158`).
  - Fixar `npx semantic-release` e plugins em versões exatas via `package.json` com lockfile em `.github/release/`.
  - **Guarda de fork:** `if: github.repository_owner == 'netboxlabs'` nos jobs que publicam (PyPI, `semantic-release`). No nosso fork, push em `release` não publica, não cria tag e não cria GitHub release.
- **`.github/dependabot.yml`** (inexistente hoje): ecossistemas `github-actions` e `pip` (raiz e `docker/*/requirements-*.txt`), semanal, agrupado.
- **`pyproject.toml` `dependencies`:**
  - Remover `grpcio` e `protobuf`: nenhum import em `netbox_diode_plugin/` fora de testes (confirmado por grep).
  - Declarar `requests` (usado em `diode/clients.py:13` e `api/authentication.py:9`).
  - `Brotli` sai com o upstream #225. `certifi` sobe com o #223, ambos via sync.
- **`docker/v4.*/requirements-diode-netbox-plugin.txt`:** a v4.4 fixa `grpcio==1.62.1`, contra `>=1.76.0` no pyproject, e todas fixam `certifi==2024.7.4`. Instalar o plugin na imagem via `pip install -e /opt/netbox/netbox/netbox_diode_plugin/..` (ou `uv pip install .`) para que o resolvedor valide o pyproject, e reduzir os requirements a extras de teste.

**FORA:**
- Mudar o runner de testes (fica no fluxo `make`).
- Pin por SHA de actions oficiais: o upstream já usa `@v7`/`@v6`. Opcional nesta SPEC, recomendado via Dependabot.

## Invariantes
- NUNCA o fork publica no PyPI, cria tag de release ou GitHub release.
- SEMPRE um push em `develop` que toca código roda lint e testes na matriz.

## Implementação
Ver Escopo. Validar com `actionlint` e `zizmor` localmente. Para o fork, confirmar via `gh api repos/aliothbl/diode-netbox-plugin/environments` que não há environment `pypi`, e acionar o `workflow_dispatch` do release num dry-run (sem gate de owner = job pulado).

### Modelo de dados
—

<!-- Alternativas: desabilitar o workflow de release só no fork pela UI do GitHub — rejeitada como única defesa (não versionada, se perde ao recriar o fork); a condição de owner é versionada e inócua upstream. -->

## Riscos
- O upstream pode não aceitar a reordenação publish/tag. Mitigação: manter a guarda de fork como patch local mínimo e documentá-la em `specs/features/upstream-sync.md`.
- Remover `grpcio`/`protobuf` pode quebrar quem importava indiretamente. Mitigação: `pip check` e testes na matriz.

## Sinais de sucesso
- Todo push em `develop` aparece com o check "Lint and tests" no GitHub. O fork nunca mais aparece com release/tag que ele mesmo gerou.

## Critério de aceite
- [ ] Push em `develop` dispara `lint-tests.yml` (evidência: run no Actions do fork) ← specctl check
- [ ] `actionlint` e `zizmor` sem erros nos dois workflows ← specctl check
- [ ] Release: gate `new-release-published`, tag antes do publish, wheel + sdist, `$GITHUB_OUTPUT`, `perf` ≠ major ← specctl check
- [ ] Guarda de owner presente; dispatch do release no fork não publica nem cria tag ← specctl check
- [ ] `pyproject` sem `grpcio`/`protobuf`, com `requests`; `pip check` limpo nas 4 imagens ← specctl check
- [ ] `dependabot.yml` ativo ← specctl check
