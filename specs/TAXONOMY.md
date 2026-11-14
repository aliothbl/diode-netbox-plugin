# TAXONOMY.md — vocabulário canônico de áreas

> Toda feature de `specs/features/` DEVE corresponder a uma área daqui (R.4/R.13). Área nova = confirmação explícita do usuário.

## Áreas

- upstream-sync — Sincronização do fork com netboxlabs/diode-netbox-plugin (develop, release, tags)
- differ-matcher — Transformer, matcher (incl. cache de match) e differ que geram o change set
- applier — Aplicação de change sets no NetBox (serializers DRF, transações, refs new_object)
- api-auth — Autenticação por introspecção no diode-auth, escopos, usuário de serviço e permissões
- api-endpoints — Views REST do plugin, limites, tratamento de erro, bypass/buffer opt-in
- branching — Integração com netbox-branching (branch padrão, header X-NetBox-Branch)
- tests-matrix — Suítes de teste por versão de NetBox (v4.4–v4.7) e ambiente docker
- packaging-ci — pyproject, dependências, CI, release no PyPI
- codegen — plugin_utils.py gerado a partir do NetBox e seu gerador
