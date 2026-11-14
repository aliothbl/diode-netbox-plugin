# SPEC-20261113-2217: Unificar as árvores de teste por versão do NetBox

**Status:** draft
**Porte:** G
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:17
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** tests, matrix, netbox-version, duplication, drift, skipUnless, version-gate, fixtures, TEST_SELECTOR, Makefile
**Features:** tests-matrix
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11, SPEC-20261113-2216-ci-dependencias-hardening (CI rodando em push antes de mexer na suíte)
**Programa:** —
**Impacto:** alto (manutenção) · **Complexidade:** média
**Estratégia upstream:** upstream-first, **obrigatória**. Uma reestruturação desse tamanho só se sustenta no fork se o upstream adotar; caso contrário, cada sync vira conflito em ~90 mil linhas. Abrir uma issue/RFC em netboxlabs/diode-netbox-plugin antes de codar.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achado P-10)
**Resumo:** São 4 árvores de teste quase idênticas (`tests/v4.4.x` … `v4.7.x`), somando ~89 mil linhas para ~15,7 mil de código de produção em `api/`. 25 arquivos são byte-a-byte idênticos nas 4, e já existe drift. Esta SPEC unifica tudo em uma árvore com gates de versão e fixtures específicos só onde a saída diverge.

## Objetivo

Cada correção hoje é copiada 4× (ex.: upstream #219 adiciona `test_customfield_version.py`, 302 linhas, em cada árvore), e testes já se perderam entre versões. O objetivo é que um teste exista **uma vez**, rode na matriz inteira e só seja pulado ou parametrizado onde o NetBox realmente difere.

## Escopo

**DENTRO:**
- Estado medido em 2026-11-13 (develop do fork):

  | Árvore | Arquivos .py | Linhas |
  |---|---|---|
  | `tests/v4.4.x` | 43 | 21.351 |
  | `tests/v4.5.x` | 43 | 22.027 |
  | `tests/v4.6.x` | 48 | 23.069 |
  | `tests/v4.7.x` | 46 | 22.817 |

  - 25 arquivos com o mesmo md5 nas 4 árvores.
  - Drift confirmado: `test_rackreservation_matcher.py` e `test_rackreservation_ingest_convergence.py` existem em v4.6.x e **não** em v4.7.x.
- Nova estrutura:
  - `netbox_diode_plugin/tests/` (única), com `tests/_version.py` expondo `NETBOX_VERSION` (de `django.conf.settings.RELEASE` / `netbox.settings.VERSION`) e decorators `requires_netbox(">=4.6")`/`skip_before`.
  - `tests/fixtures/<versão>/` apenas para saídas esperadas que divergem (ex.: campos novos de modelo em 4.6/4.7).
- `Makefile:21`: `TEST_SELECTOR` passa a apontar para `tests/` (sem `$(NETBOX_MINOR_VERSION)`). `NETBOX_MINOR_VERSION` continua escolhendo o `docker/v4.x.x`.
- Recuperar testes perdidos pelo drift: os de rackreservation (para 4.7) e `PluginCompatibilityTestCase` (hoje só em 4.7, avaliar todas).
- Ferramenta de apoio (`scripts/test_tree_diff.py`, descartável em `tmp/` da SPEC) que lista, por arquivo, as diferenças entre as 4 árvores para guiar o merge.

**FORA:**
- Mudar o runner de `manage.py test` para pytest.
- Reduzir a matriz de versões suportadas.

## Invariantes
- NUNCA reduzir o número de testes executados por versão: contagem pós-unificação ≥ contagem atual, por versão.
- SEMPRE a matriz do CI cobre as mesmas 4 versões.

## Plano de migração

| Etapa | Descrição | Saída verificável |
|---|---|---|
| 0 | RFC/issue upstream com números desta SPEC e proposta de layout; só seguir com aceite (ou decisão explícita do owner de manter só no fork) | link da issue |
| 1 | Baseline: rodar a matriz e salvar a contagem de testes por versão (`Ran N tests`) em `evidence/baseline.txt` | arquivo com 4 contagens |
| 2 | Criar `tests/` unificado com os 25 arquivos idênticos; remover as cópias; Makefile apontando para o novo selector **e** para as árvores antigas (os dois rodam) | matriz verde, contagem igual |
| 3 | Migrar arquivos que diferem só em cabeçalho/copyright | idem |
| 4 | Migrar arquivos com divergência real, usando `requires_netbox` ou fixtures por versão, um PR por grupo (matcher, applier, differ, transformer, views) | idem por PR |
| 5 | Reintroduzir os testes perdidos pelo drift (rackreservation em 4.7 etc.) | contagem ≥ baseline + recuperados |
| 6 | Remover `tests/v4.*` e a seleção antiga no Makefile | `find netbox_diode_plugin/tests -path '*v4.*' -name '*.py'` vazio |

## Implementação
Ver Plano de migração. Cada etapa é um PR independente, mergeável e verde. O gate de versão usa comparação semântica (`packaging.version`). Não usar o nome do diretório.

### Modelo de dados
—

<!-- Alternativas:
- Gerar as 4 árvores a partir de templates (jinja): rejeitada, porque mantém a duplicação no artefato e complica a depuração.
- Manter as árvores e adicionar um check de drift no CI: rejeitada como solução final. Serve só como etapa intermediária se o upstream recusar a unificação.
-->

## Riscos
- O upstream recusa a reestruturação. Mitigação: não aplicar no fork. A alternativa de baixo custo é um check de drift no CI (que avisa quando um arquivo idêntico nas 4 árvores diverge), proposto no lugar.
- Comportamento diferente por versão escondido em diferenças sutis de fixture. Mitigação: as etapas 3 e 4 são guiadas pelo diff gerado e a contagem de testes é comparada a cada etapa.
- Tempo de CI: sem mudança, porque cada versão continua rodando a sua seleção.

## Sinais de sucesso
- Uma correção upstream típica passa a tocar 1 arquivo de teste em vez de 4, e o tamanho total de `tests/` cai para algo próximo de ¼ do atual.

## Critério de aceite
- [ ] Baseline de contagem de testes por versão registrado | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v docker-compose-netbox-plugin-test 2>&1 | grep -E '^Ran [0-9]+ tests'; done`
- [ ] Árvore única; nenhuma `tests/v4.*` restante | verify: `test -z "$(find netbox_diode_plugin/tests -path '*v4.*' -name '*.py')"`
- [ ] Matriz completa verde com contagem por versão ≥ baseline | verify: `for v in v4.4.10 v4.5.5 v4.6.10 v4.7.0; do make NETBOX_VERSION=$v docker-compose-netbox-plugin-test || exit 1; done`
- [ ] Testes de rackreservation executando em 4.7 | verify: `make NETBOX_VERSION=v4.7.0 TEST_FLAGS="-k RackReservation" docker-compose-netbox-plugin-test`
- [ ] RFC/issue upstream aberta e decisão registrada no journal | evidence: manual @aliothbl
