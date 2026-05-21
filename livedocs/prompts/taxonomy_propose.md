# Tarefa
Proponha uma taxonomia de guias de help center para este SaaS,
baseada nos sinais de código fornecidos.

# Orientação do mantenedor
{% if guidance_text %}{{ guidance_text }}{% else %}(nenhuma){% endif %}

# Sinais
## Rotas ({{ routes|length }})
{% for r in routes %}- `{{ r.path }}` — {{ r.file }}
{% endfor %}

## Labels de menu / i18n ({{ i18n|length }} chaves)
{% for k in i18n %}- `{{ k.key }}` → {{ k.values_by_lang|tojson }}
{% endfor %}

## Modelos de domínio ({{ models|length }})
{% for m in models %}- {{ m.name }} ({{ m.kind|default('model') }}) — campos: {{ m.fields|join(", ") }}
{% endfor %}

## Grafo (resumo top-level)
{% if graph_summary %}{{ graph_summary }}{% else %}(grafo indisponível){% endif %}

# O que entregar
Responda **APENAS** com JSON estrito, sem comentários, sem prosa antes/depois:

```json
{
  "capabilities": [
    {"slug": "kebab-case", "title": "Título humano", "summary": "uma linha",
     "code_anchors": ["src/billing/**", "src/payments/**"]}
  ],
  "journeys": [
    {"slug": "kebab-case", "title": "Título humano", "summary": "uma linha",
     "capability_refs": ["slug1", "slug2"]}
  ]
}
```

# Regras
- Capacidades: 10-25 itens. Cada uma = unidade de negócio reconhecível pelo
  usuário final do SaaS. Use a orientação do mantenedor para desempatar nomes.
- Jornadas: 3-10 itens. Só crie quando agregam valor cross-cutting; cada
  jornada referencia 2+ capacidades.
- NÃO crie um guia por rota; rotas viram seções dentro de capacidades.
- Slugs em kebab-case, no idioma **{{ lang }}**.
- `code_anchors` são globs do repositório, apontando para os arquivos /
  pastas que provavelmente cobrem a capacidade.
- Se um sinal estiver ausente (rotas vazias, etc.), faça a melhor inferência
  a partir do que sobrou.
