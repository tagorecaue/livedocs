# Tarefa — Split de capacidade em artigos

Você vai propor uma divisão da capacidade abaixo em **2 a 7 artigos**
distintos. Cada artigo vira uma página independente no help center
(Chatwoot). A capacidade é o contêiner (categoria); os artigos são as
páginas dentro.

# Capacidade-alvo
- slug: `{{ capability.slug }}`
- título: {{ capability.title }}
- resumo: {{ capability.summary }}
- code_anchors da capacidade:
{% for a in capability.code_anchors %}  - `{{ a }}`
{% endfor %}

# Orientação do mantenedor
{% if guidance_text %}{{ guidance_text }}{% else %}(nenhuma){% endif %}

# Sinais do código tocados por essa capacidade

## Rotas ({{ routes|length }})
{% for r in routes %}- `{{ r.path }}`{% if r.file %}  ({{ r.file }}){% endif %}
{% endfor %}

## Models ({{ models|length }})
{% for m in models %}- {{ m.name }}{% if m.file %}  ({{ m.file }}){% endif %}
{% endfor %}

{% if graph_nodes %}## Top nós do grafo
{% for n in graph_nodes %}- {{ n }}
{% endfor %}{% endif %}

# Regras de saída
- **Idioma**: {{ lang }}.
- Entre **2 e 7 artigos**.
- Slugs em **kebab-case**, únicos dentro da capacidade.
- **No máximo um artigo com `is_intro=true`** (zero é aceitável se a capacidade for pequena/homogênea). O intro é a "visão geral" da capacidade — resume o domínio e linka os irmãos. Não duplica conteúdo dos irmãos.
- `code_anchors` de cada artigo devem ser um **subset/refinamento** dos anchors da capacidade pai. Não invente paths fora do escopo. Se um artigo cobre um subconjunto bem definido, restrinja seu glob; se cobre tudo (intro), pode repetir os anchors da capacidade.
- Cada artigo tem um foco operacional claro (uma tarefa do usuário, um fluxo, uma tela coesa). Evite artigos genéricos do tipo "outros assuntos".

# Output (JSON estrito — somente JSON, sem prosa antes/depois)
```json
{
  "articles": [
    {
      "slug": "introducao",
      "title": "Visão geral de ...",
      "summary": "...",
      "is_intro": true,
      "code_anchors": ["..."]
    },
    {
      "slug": "...",
      "title": "...",
      "summary": "...",
      "is_intro": false,
      "code_anchors": ["..."]
    }
  ]
}
```
