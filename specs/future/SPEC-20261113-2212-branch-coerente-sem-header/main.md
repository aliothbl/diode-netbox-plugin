# SPEC-20261113-2212: Branch coerente quando falta `X-NetBox-Branch`, e uma consulta de Branch por requisição

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-13 22:12
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** netbox-branching, X-NetBox-Branch, Setting.branch, _get_branch_schema_id, _add_branch_to_result, N+1, default-branch, fail-closed
**Features:** branching
**Branch:** _(a definir na ativação)_
**Depende de:** SPEC-20261113-2132-sync-upstream-develop-2026-11
**Programa:** —
**Impacto:** alto · **Complexidade:** baixa
**Estratégia upstream:** upstream-first. Abrir PR em netboxlabs/diode-netbox-plugin e carregar a mudança no fork só até o merge.
**Origem:** diagnóstico 2026-11-13 (diode/specs/DIAGNOSTICO-2026-11-13.md, achados P-3 e P-8)
**Resumo:** Sem o header, o plugin **anota** o resultado com a branch do Setting, mas lê e escreve no **main**, porque nada ativa a branch. Esta SPEC faz o plugin recusar com 400 uma requisição que deveria ir para uma branch mas veio sem o header. Também troca o `Branch.objects.get` por entidade por uma única consulta por requisição.

## Objetivo

O resultado devolvido ao reconciler tem que descrever onde a mudança realmente aconteceu. Hoje, com `Setting.branch_id` configurado e sem header, a resposta diz "branch X" e a escrita vai para main. O server mitiga isso (diode#586, fail-closed), mas o plugin continua aceitando a requisição inconsistente.

## Escopo

**DENTRO:**
- `_get_branch_schema_id` (`netbox_diode_plugin/api/views.py:197-215`). Hoje, sem `X-NetBox-Branch`, ele cai em `Setting.branch.schema_id` (`views.py:201-210`), e só o middleware do netbox-branching ativa a branch, a partir de header, query `_branch` ou cookie (`netbox_branching/middleware.py`). Portanto, ao cair no fallback, a branch **não** está ativa. Nova regra:
  - Com header: usar o header. A branch está ativa pelo middleware.
  - Sem header e com `Setting.branch` definido: **400** `{"request": {"branch": ["X-NetBox-Branch required: default branch <name> is configured"]}}`.
  - Sem header e sem Setting: main, sem anotação.
- `_add_branch_to_result` (`views.py:218-230`): recebe o objeto `Branch` já resolvido (ou `None`) em vez do `schema_id`. Hoje faz `Branch.objects.get(schema_id=...)` **por entidade** (chamado em `views.py:355`, `:438` e `:701`). Resolver uma vez por requisição em `post()`.
- Comparar o header com a branch ativa (`request.active_branch`, setado pelo middleware em `middleware.py:60`). Se divergirem, retornar 400.
- `Setting.branch` (`netbox_diode_plugin/models.py:54-70`) faz consulta a cada acesso e engole qualquer exceção. Passa a capturar só `ObjectDoesNotExist`/`ImportError` e logar o resto.

**FORA:**
- Ativar a branch do Setting no plugin (contextvar `active_branch`), rejeitado: duplica a lógica do middleware e esconde o erro de configuração do reconciler. Confirmar o comportamento do reconciler, que já envia o header (`diode-server/netboxdiodeplugin/client.go:346`, `:440`).
- Endpoint `default-branch/` (`views.py:713`): mantido.

## Invariantes
- SEMPRE: a branch anotada no resultado = a branch em que leitura e escrita ocorreram.
- NUNCA uma escrita vai para main quando há branch padrão configurada e a requisição não declarou nenhuma.

## Implementação
Ver Escopo. A mudança fica toda em `api/views.py` e `models.py`, com teste por endpoint (`generate-diff`, `bulk-plan`, `bulk-plan-apply`, `apply-change-set`, `bulk-apply`) nos cenários com header, sem header com Setting e sem nenhum dos dois. Os testes ficam condicionados a `netbox_branching` instalado, como já é feito nos testes de branch existentes.

### Modelo de dados
—

<!-- Alternativas: ativar a branch do Setting via contextvar quando falta o header — rejeitada (ver FORA). -->

## Riscos
- Clientes que dependem do fallback silencioso (chamadas manuais à API sem header) passam a receber 400. Mitigação: a mensagem do 400 cita o nome da branch e o header esperado, e a nota entra no CHANGELOG.
- Reconciler com cache frio do default-branch e sem header. O #586 do server já faz fail-closed, então o 400 do plugin é coerente com ele.

## Sinais de sucesso
- Nenhum resultado com `branch` preenchido cujas mudanças aparecem em main. O número de queries do bulk passa a ser constante em relação à branch.

## Critério de aceite
- [ ] Sem header + Setting com branch → 400 em todos os endpoints de plano/apply ← specctl check
- [ ] Com header → anotação = branch ativa; header divergente da branch ativa → 400 ← specctl check
- [ ] `Branch.objects.get` executado 1× por requisição bulk (assertNumQueries) ← specctl check
- [ ] `Setting.branch` não engole exceções genéricas ← specctl check
