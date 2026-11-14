# SPEC-20261114-1747: Atualizar netbox-branching no ambiente de teste (1.2.0 → 1.2.3)

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:47
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** netbox-branching, dependência, requirements, docker, v4.7.x, v4.6.x, #672, #675
**Features:** branching, tests-matrix
**Branch:** _(a definir na ativação)_
**Programa:** `aliothbl/diode:specs/programs/diode-stack-hardening.md`
**Relacionadas:** `aliothbl/netbox-branching:specs/DIAGNOSTICO-2026-11-14.md` (seção "Versões")
**Origem:** diagnóstico do netbox-branching de 2026-11-14.
**Resumo:** O ambiente docker do plugin fixa `netboxlabs-netbox-branching==1.2.0` para NetBox 4.7 (`docker/v4.7.x/requirements-diode-netbox-plugin.txt:6`). As versões 1.2.1–1.2.3 corrigem dois problemas que atingem o Diode: #672 (branch indisponível gerava 500 em vez de 400) e #675 (scripts e webhooks disparados por escrita via API quebravam no worker com NetBox 4.7).

## Objetivo

Testar o plugin contra a versão do netbox-branching que corrige #672/#675, para que a suíte e o benchmark reflitam o comportamento atual.

## Escopo

**DENTRO:**
- `docker/v4.7.x/requirements-diode-netbox-plugin.txt`: `netboxlabs-netbox-branching==1.2.3`.
- Avaliar `docker/v4.6.x` (hoje 1.0.3; a série compatível com 4.4–4.6 vai até 1.1.3, segundo `COMPATIBILITY.md` do netbox-branching) e registrar a decisão no journal.
- Rodar a suíte v4.7.0 inteira.
- Se a versão mudar o comportamento do branch padrão, atualizar a feature `branching`.

**FORA:**
- Pin em instalações de produção, que fica a cargo de quem opera.

## Invariantes
- Suíte v4.7.x verde com a versão nova.

## Critério de aceite
- [ ] Pin atualizado e suíte v4.7.0 verde ← specctl check (`NETBOX_VERSION=v4.7.0 make docker-compose-netbox-plugin-test`)
- [ ] Decisão sobre v4.6.x registrada no journal | evidence: manual @aliothbl
