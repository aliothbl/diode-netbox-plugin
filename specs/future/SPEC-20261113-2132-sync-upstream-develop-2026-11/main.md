# SPEC-20261113-2132: Sincronizar fork `diode-netbox-plugin` com upstream (develop/release, nov/2026)

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-13 21:32
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** upstream, sync, fork, netboxlabs, customfield-cache, multi-worker, tags_resolved, certifi, brotli
**Features:** upstream-sync, differ-matcher
**Branch:** _(a definir na ativação)_
**Programa:** `diode/specs/programs/diode-stack-hardening.md`
**Relacionadas:** `diode/specs/future/SPEC-20261113-2130-sync-upstream-develop-2026-11/main.md` (par de #227 = diode #600)
**Origem:** diagnóstico de 2026-11-13 (`diode/specs/DIAGNOSTICO-2026-11-13.md`, §5).
**Resumo:** Fast-forward de `develop` (+5 commits) e `release` (+15), trazendo a invalidação de cache de custom fields entre workers (#219/#222), `tags_resolved` no plano (#227), `certifi` (#223) e a remoção do Brotli (#225).

## Objetivo

O fork não tem commits próprios. Os 5 commits ausentes incluem uma correção de **consistência entre processos**: sem #219, um gunicorn/uwsgi com N workers serve definições de custom field desatualizadas até o restart, o que gera diffs errados. Também incluem a contraparte de #600 do server (`tags_resolved`).

## Escopo

**DENTRO:**
- `git merge --ff-only upstream/develop` em `develop`:
  - `9947f12` #219 — `api/customfield_version.py` (versão compartilhada no cache do NetBox; cada worker compara e limpa o cache local).
  - `c209483` #222 — um clearer que levanta exceção não interrompe os demais.
  - `208a5db` #223 — `certifi>=2026.10.19`.
  - `b675a5c` #225 — remove a dependência não usada `Brotli`.
  - `8c3a3bb` #227 — `tags_resolved` nas mudanças planejadas (`api/differ.py`).
- `git merge --ff-only upstream/release` em `release`.
- Avaliar a branch `mon-359-cooling-components-template-instantiated`: idêntica à upstream (0/0). Manter como espelho ou apagar.
- Rodar a matriz de testes do `Makefile` para ao menos a versão de NetBox em uso (`tests/v4.x.x`).

**FORA:**
- Refatoração da duplicação `tests/v4.4.x … v4.7.x` (SPEC própria).

## Invariantes
- NUNCA reescrever histórico de `develop`/`release`.
- SEMPRE subir plugin e server (diode #600) na mesma janela de manutenção, para que `tags_resolved` apareça ponta a ponta.

## Implementação

```bash
git fetch upstream --tags
git switch develop && git merge --ff-only upstream/develop
git switch release && git merge --ff-only upstream/release
make docker-compose-netbox-plugin-test   # ou o alvo de teste equivalente do Makefile para a versão em uso
git push origin develop release --follow-tags
```

#219 depende do backend de cache do NetBox (Redis) ser compartilhado entre workers, o que já é padrão em NetBox ≥4.

### Modelo de dados
— (sem migration Django; a versão de CF vive no cache).

## Riscos
- Instalações com `CACHES` local (LocMem) por worker não ganham a invalidação cruzada. Mitigação: documentar a exigência de cache compartilhado.
- Remoção do Brotli: verificar que nenhum ambiente nosso importa `brotli` via o plugin (`grep -r brotli` nos manifests de deploy).

## Sinais de sucesso
- Editar um custom field no NetBox reflete no próximo `generate-diff` em **todos** os workers, sem restart.

## Critério de aceite
- [ ] `develop`/`release` sem atraso para upstream ← specctl check
- [ ] Testes da versão de NetBox em uso verdes ← specctl check
- [ ] Teste manual: alterar choices de um custom field e gerar diff via 2 workers diferentes, ambos coerentes | evidence: manual @aliothbl
