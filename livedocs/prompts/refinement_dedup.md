# Tarefa
Você recebeu uma lista de perguntas pendentes geradas durante a documentação automática deste SaaS. Várias podem ser equivalentes (mesma dúvida, fraseados diferentes, contextos próximos). Agrupe perguntas equivalentes em clusters.

# Orientação do mantenedor
{% if guidance_text %}{{ guidance_text }}{% else %}(nenhuma){% endif %}

# Perguntas pendentes
{% for q in questions %}
- id: `{{ q.id }}` · guia: `{{ q.guide_slug }}` · confiança: {{ q.confidence }}
  pergunta: {{ q.question }}
  suposição provisória: {{ q.provisional_answer or "(nenhuma)" }}
{% endfor %}

# O que fazer
1. Identifique clusters de perguntas equivalentes (mesma intenção, mesma resposta esperada).
2. Para cada cluster com 2+ itens, escolha um `canonical_id` (o id mais representativo) e marque os demais como `merged_ids`.
3. Para cada cluster, escreva uma `canonical_question` clara em pt-BR (ou idioma original) que sintetize as variações. Se a pergunta canônica original já está boa, repita-a.
4. Perguntas sem cluster (únicas) vão em `unique_ids`.

# Output (JSON estrito — só o JSON)
```json
{
  "clusters": [
    {"canonical_id": "Q3", "canonical_question": "...", "merged_ids": ["Q7", "Q11"]}
  ],
  "unique_ids": ["Q1", "Q2"]
}
```
