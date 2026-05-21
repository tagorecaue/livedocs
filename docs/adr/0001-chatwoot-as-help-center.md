# ADR 0001 — Chatwoot como help center publicado

- Status: Aceito
- Data: 2026-05-21

## Contexto

LiveDocs gera `.md` localmente, mas o consumidor final dos guias
(cliente do SaaS documentado) precisa de um help center web com
busca, navegação, branding e capacidade do humano editar
visualmente. Alternativas consideradas:

- **Mintlify** — produto inspirador, mas SaaS pago, sem controle
  do dado, sem editor humano nativo.
- **Help center custom (herdar do nexa)** — possível, mas atrasa
  o MVP em semanas; precisaríamos construir editor, autenticação,
  upload de imagem.
- **Docusaurus / outros geradores estáticos** — não têm editor
  visual; humano teria que editar `.md` direto.
- **Chatwoot** — open source, já deployado pelo autor, tem help
  center nativo com editor visual, upload de imagem, multi-idioma,
  API pra publicar e sincronizar.

## Decisão

Adotar Chatwoot como destino oficial de publicação no MVP.
LiveDocs publica via API do Chatwoot e sincroniza de volta para
preservar edições humanas.

## Consequências

Positivas:
- Zero esforço de construir help center próprio
- Editor visual e upload de imagens já resolvidos
- Reaproveita deploy existente do autor
- Mesma plataforma já serve suporte ao cliente (chat + docs)

Negativas / a aceitar:
- Acoplamento ao modelo de dados do Chatwoot (Article, Category,
  Portal). Migrar pra outro help center exige adaptador.
- Sincronização bidirecional traz complexidade real: detectar
  edição humana, reconciliar, preservar imagens, gerar diff.
- Multi-tenancy do LiveDocs precisa mapear cada workspace pra um
  portal Chatwoot.

## Trade-off principal

Velocidade de MVP e qualidade de editor visual vencem
flexibilidade futura de troca de plataforma. Se um cliente quiser
outra ferramenta no futuro, construímos adaptador específico —
não antecipamos.