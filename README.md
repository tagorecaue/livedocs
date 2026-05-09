<div align="center">

# LiveDocs

**Documentação viva para SaaS — guiada por entrevista, alimentada por agente, sempre alinhada ao código.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)]()

</div>

---

LiveDocs transforma o conhecimento que vive no código + na cabeça do dev em **guias de produto e técnicos pareados**, mantidos vivos enquanto o sistema evolui.

A premissa: você não senta pra "escrever documentação". Você responde perguntas direcionadas — perguntas que um agente IA faz depois de ler seu código. As respostas viram guias `.md` em pt-BR, en (ou idioma da sua escolha) que ficam **na sua máquina**, no seu repositório, sob seu controle.

Sem cloud obrigatório. Sem captura de código. Sem lock-in.

## Status

**v0 / alpha — dogfood interno.** A versão pública vai aparecer aqui quando o autor terminar de validar o fluxo na própria empresa. Se você se interessou, abre uma issue — feedback inicial é ouro.

## Princípios

- **AGPL-3.0** — open-source de verdade. Forks têm que abrir.
- **Local-first** — `.md` e estado moram na sua máquina. Cloud é opcional, sempre.
- **BYOA (Bring Your Own Agent)** — Claude Code, Codex, Hermes, Cursor, Ollama. Você escolhe.
- **Multi-idioma desde o dia 1** — auto-detecta idioma do sistema, confirma na primeira execução.
- **Guias pareados produto + técnico** — mesmo conhecimento, dois consumidores: cliente final (helpcenter, widget) vs dev/IA (MCP, onboarding).
- **Sempre humano-no-loop** — IA propõe, dev aprova. Sem commit silencioso.

## v0 — o que existe hoje

```bash
livedocs              # detecta onde você parou e oferece próximo passo
livedocs init         # configura projeto pela primeira vez
livedocs new <slug>   # começa um guia novo
livedocs continue     # retoma entrevista em andamento
livedocs status       # estado de todos os guias
livedocs review       # revisa coerência, links, front-matter
```

Provider único no v0: **Claude Code CLI** (recomendado). Outros entram em v0.5.

## Roadmap

| v | Conteúdo |
|---|----------|
| **v0** (esta) | CLI de entrevista + geração local de guias |
| v0.5 | Integração com graphify (grafo de código), modo "scan completo" |
| v1 | Dashboard web local + MCP server local (servir guias pra Claude Code/Cursor) |
| v2 | Cloud free tier — helpcenter público + widget conversacional |
| v3 | Plano pago — custom domain, video, analytics, multi-user |

## Contribuir

Não estamos abertos a contribuições externas ainda — produto está em validação. Quando estiver, este aviso some.

## Licença

[AGPL-3.0-or-later](LICENSE). Ver `LICENSE` no repo.
