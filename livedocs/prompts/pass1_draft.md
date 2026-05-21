# Tarefa
Escreva o RASCUNHO INICIAL do guia "{{ title }}" ({{ kind }}).

# Orientação do mantenedor
{% if guidance_text %}{{ guidance_text }}{% else %}(nenhuma){% endif %}

# Estilo
{% if style %}{{ style }}{% else %}(estilo padrão){% endif %}

# Menu completo do help center (índice apenas, sem corpo)
{% for item in menu_index %}- [{{ item.kind }}] `{{ item.slug }}` — {{ item.title }}{% if item.summary %} — {{ item.summary }}{% endif %}
{% for a in item.articles %}    - `{{ item.slug }}/{{ a.slug }}` — {{ a.title }}{% if a.is_intro %}  (intro){% endif %}
{% endfor %}{% endfor %}

# Este guia
- slug: `{{ slug }}`
- title: {{ title }}
- kind: {{ kind }}
- summary: {{ summary }}
{% if capability_title %}
# Artigo dentro de capacidade
- capacidade pai: {{ capability_title }}
- artigos irmãos:
{% if siblings %}{% for s in siblings %}  - `{{ s.slug }}` — {{ s.title }}
{% endfor %}{% else %}  (nenhum — único artigo da capacidade){% endif %}
{% if is_intro %}- **Este artigo é INTRODUTÓRIO.** Resuma o domínio inteiro da capacidade. Linke os irmãos com `[TODO:link=<sibling-slug>]` (ou `[TODO:link={{ slug.split('/')[0] }}/<sibling-slug>]` se for ambíguo). NÃO entre no detalhe operacional dos irmãos — cada um tem seu próprio artigo.{% endif %}
{% endif %}
# Código relevante para este guia
Leia os arquivos que casam com os globs abaixo. Use a tool Read/Glob/Grep:

{% for a in code_anchors %}- `{{ a }}`
{% endfor %}

# Regras
- Você está num CONTEXTO ISOLADO. NÃO assume que outros guias existem com conteúdo X — só sabe os títulos do menu.
- Se você quiser referenciar outro guia, escreva `[TODO:link={slug}]` no lugar do link real (formato `<cap>/<article>` para articles, ou só o slug para journeys). A passada 2 resolve.
- Se encontrar algo que o código não revela (intenção de UX, porquê de uma regra de negócio, integração externa, conexão implícita), NÃO invente. Registre como pergunta pendente.
- Gere DOIS arquivos por guia usando a tool Write:
    - `{{ product_path }}` (guia de produto, idioma {{ lang }})
    - `{{ tech_path }}`    (guia técnico, mesmo idioma)
- Front-matter obrigatório nos dois (slug, title, kind, status="drafted", generated_at).

# Screenshots — TODOs estruturados
Quando o artigo mencionar uma TELA ou ROTA concreta da aplicação (caminhos como `/projects/new`, `/settings/billing`, telas do app), insira IMEDIATAMENTE APÓS o parágrafo que menciona, em linha separada, um marcador no formato:

> [!TODO:screenshot]
> Rota: `/path/da/rota`
> Descrição: <o que essa tela mostra ou em que estado capturá-la>

Use a sintaxe de admonition do GitHub/Obsidian acima EXATAMENTE como mostrada (com o `>` no início de cada linha do bloco). Não confunda com `[TODO:link=...]` que serve pra linkar outros guias.

Regras:
- Insira o marcador APENAS no `.md` de produto. NÃO insira no `.tech.md`.
- Uma rota por marcador. Se um parágrafo menciona 3 telas, crie 3 marcadores.
- Se a "rota" é abstrata (ex.: "tela de relatórios") e você não tem caminho concreto no código, OMITA o marcador — não invente.
- Liste TODOS os marcadores que você inserir no campo `screenshot_todos` do JSON de saída.

# Output (JSON estrito — somente JSON, sem prosa antes/depois)
```json
{
  "files_written": ["{{ product_path }}", "{{ tech_path }}"],
  "pending_questions": [
    {"question": "...", "provisional_answer": "...", "confidence": "low"}
  ],
  "screenshot_todos": [
    {"route": "/projects/new", "description": "Tela inicial do wizard de criação"}
  ]
}
```
