# Feature: upstream-sync

**Keywords:** upstream, fork, netboxlabs, fast-forward, develop, release, tags
**Arquivos principais:**
  - (processo — sem código)
  - .github/workflows/release.yaml
**Resumo:** Como o fork aliothbl/diode-netbox-plugin acompanha netboxlabs/diode-netbox-plugin: fast-forward de develop/release, sem commits próprios fora de specs/.

## Specs desta feature

### Concluídas
—

### Planejadas (future/)
- SPEC-20261113-2132-sync-upstream-develop-2026-11 | Sincronizar develop (+5) e release (+15) | fork atrasado, inclui #219 e #227

## Estado atual

Em 2026-11-13 o fork tem **0** commits próprios em `develop`, que está 5 commits atrás de `upstream/develop` (#219, #222, #223, #225, #227) e 15 atrás em `release`. A branch `mon-359-cooling-components-template-instantiated` é idêntica à do upstream. O remote `upstream` aponta para `https://github.com/netboxlabs/diode-netbox-plugin.git`. A única customização prevista é o diretório `specs/` na raiz, que nunca conflita com o upstream.

## Decisões arquiteturais ativas
- DEC-20261113-2132-fork-espelho-ff [ativa] (SPEC-20261113-2132-sync-upstream-develop-2026-11) — o fork é espelho: sync por `merge --ff-only` (ou `--no-ff` quando `specs/` estiver commitado), sem rebase. Correções de código vão upstream-first; patch local só como ponte até o merge. Trade-off: dependemos do ritmo de revisão do upstream.
- DEC-20261113-2151-diretorio-specs-na-raiz [ativa] (SPEC-20261113-2132-sync-upstream-develop-2026-11) — o processo SDD vive em `specs/` (não `docs/`), para não colidir com arquivos do upstream. Trade-off: diverge do layout `docs/` do wynk_crm.

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261113-2132 | #227 (`tags_resolved`) só tem efeito ponta a ponta com o diode server #600 também atualizado (2026-11-13) — subir os dois na mesma janela.
- SPEC-20261113-2216 | o workflow de release herdado publica no PyPI via trusted publishing e cria tag/GitHub release; no fork, push em `release` não deve publicar (2026-11-13) — guarda de owner na SPEC-20261113-2216.
