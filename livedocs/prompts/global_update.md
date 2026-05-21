# Tarefa
Você escreveu este guia antes. Agora o mantenedor respondeu perguntas pendentes que estavam abertas. Atualize o guia incorporando as respostas.

# Orientação do mantenedor
{% if guidance_text %}{{ guidance_text }}{% else %}(nenhuma){% endif %}

# Guia atual
## Arquivo de produto — `{{ product_path }}`
```markdown
{{ product_content }}
```

## Arquivo técnico — `{{ tech_path }}`
```markdown
{{ tech_content }}
```

# Perguntas respondidas relevantes a este guia
{% for qa in qas %}
- id: `{{ qa.id }}` · confiança original: {{ qa.confidence }}
  pergunta: {{ qa.question }}
  suposição provisória que estava no rascunho: {{ qa.provisional_answer or "(nenhuma)" }}
  RESPOSTA do mantenedor: {{ qa.answer }}
{% endfor %}

# O que fazer
- Substitua as suposições provisórias pelas respostas reais quando aplicável.
- Remova marcadores `[TODO:pergunta=...]` que foram respondidos.
- Se uma resposta invalida um trecho, reescreva o trecho.
- NÃO mude links e termos já harmonizados na passada 2 sem motivo.
- Reescreva os arquivos via tool Write (sobrescrevendo com a versão atualizada).

# Output (JSON estrito — só o JSON)
```json
{
  "files_modified": ["{{ product_path }}", "{{ tech_path }}"],
  "changes_summary": "uma linha resumindo o que mudou"
}
```
