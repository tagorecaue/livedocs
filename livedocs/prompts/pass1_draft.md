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

# Output (JSON estrito — somente JSON, sem prosa antes/depois)
```json
{
  "files_written": ["{{ product_path }}", "{{ tech_path }}"],
  "pending_questions": [
    {"question": "...", "provisional_answer": "...", "confidence": "low"}
  ]
}
```
