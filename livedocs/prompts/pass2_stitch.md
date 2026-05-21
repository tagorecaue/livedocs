# Tarefa
Costure este guia ao restante do help center.

# Este guia (slug: `{{ slug }}`, kind: {{ kind }})

## Arquivo de produto — `{{ product_path }}`
```markdown
{{ product_content }}
```

## Arquivo técnico — `{{ tech_path }}`
```markdown
{{ tech_content }}
```

# Índice dos demais guias
{% for o in index_others %}
## `{{ o.slug }}` — {{ o.title }}
- summary: {{ o.summary }}
- primeiro parágrafo: {{ o.first_paragraph }}
{% endfor %}

# Placeholders [TODO:link=...] detectados
{% if todos %}{% for s in todos %}- `{{ s }}`
{% endfor %}{% else %}(nenhum){% endif %}

# O que fazer
1. Para cada `[TODO:link={slug}]`, substitua pelo link Markdown real se o slug existe no índice. Se não existe, registre como pergunta pendente em `new_pending_questions` ("Quis linkar {slug} mas não achei guia correspondente") e mantenha no array `todos_unresolved`.
2. Onde o texto menciona algo que CLARAMENTE corresponde a outro guia (mesmo sem TODO), proponha link inline.
3. Harmonize terminologia: se este guia usa um termo divergente do dominante no menu, ajuste.
4. Sinalize contradições: se este guia afirma X mas outro guia afirma not-X, anote em `contradictions`.
5. NÃO reescreva conteúdo conceitual. Mude o mínimo: links, termos, marcadores de contradição.

Reescreva os arquivos usando a tool Write (sobrescrevendo com a versão atualizada).

# Output (JSON estrito — somente JSON, sem prosa antes/depois)
```json
{
  "files_modified": ["{{ product_path }}", "{{ tech_path }}"],
  "links_added": 0,
  "todos_resolved": 0,
  "todos_unresolved": [],
  "contradictions": [
    {"this_guide_says": "...", "other_guide": "slug", "other_says": "..."}
  ],
  "new_pending_questions": [
    {"question": "...", "provisional_answer": "...", "confidence": "low"}
  ]
}
```
