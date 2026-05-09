O produto será um MVP para documentação viva de um saas.
Vamos transformar o workflow manual que tenho feito para documentar a Regulairzei em um produto mais visual com UI.
Carregue a skill de living-docs-with-graph para entender melhor.

qual objetivo do meu projeto e tenho questões de design ainda não claras:
 - Ser multi organização
 - Ter cadastro de projetos ou workspaces
 - Em um workspace, permitir conectar a um ou mais codebases (repos git)
 - utilizar o https://github.com/safishamsi/graphify para criar um grafo dos repositórios conectados (cliente pode subir backend e UI de um produto por exemplo)
 - Com base no grafo quero escanear e perguntar ao cliente por onde começar, sugerir um fluxo do sistema.
 - Cada novo fluxo passa por uma investigação feit apela IA, e uma entrevista.
 - A idéia é que tenhamos uma UI para o usuário responder a entrevista, a cada resposta feita pelo usuário a UI chega no histórico da base de conhecimento se existe alguma contradição ou erro, e sugere um ajuste que pode ser ignorado ou aceito, ou apenas marca como validado.
 - Quando a entrevista termina na UI o cliente clica em OK e o sistema gera o primeiro documento tecnico e de produto.
 - A idéia é que cada workspace tenha 2 help center, um para desenvolvedores e outro para clientes.
 - O sistema sugere o próximo passo e pergunta se é o caminho que o usuário quer seguir, e assim por diante ele vai documentando o sistema, a cada nova rodada, o ssitema olha para tudo o que já foi feito e cria links e sugere ajustes em outros documentos.
 - O cliente terá liberdade de alterar manualmente os documentos, incluir prints de tela ou alterar textos, a cada alteração isso a IA valida e sugere alterações ou links com outros documentos.
 - Toda vez que o sistema detecta uma alteração no código, ele deve entender a alteração, e se necessário alterar a documentação vinculada com aquele código, para isso pode usar a documentação tecnica que inclui detalhes sobre os arquivos daquele escopo.
 - Tanto a documentação tecnica como a de produto são automaticamente atualizadas para refletir as alterações no código.
 - Caso a IA tenha duvidas, ela cria uma nova entrevista que fica em uma area pendente para ser respondida quando o cliente desejar. A cada resposta do cliente, a IA pode revalidar a lista de perguntas para ver se uma resposta já sana as outras, mostra isso para o usuário que confirma que se trata da mesma coisa, ou mantem a outra pergunta, para eventualmente adicionar mais detalhes.
 - Usuário pode decidir por permitir documentação viva, ou manter em draft para que seja publicado por ele mesmo.
 - Print screens não são automaticamente atualizados ou capturados, sendo importante uma area de revisão para indicar possível necessidade de atualização do material por um humano.
 - Quero manter tudo em arquivos .md separados por organização e workspace, banco de dados é para estruturas de operação do sistema, não para o conhecimento.
 - importante ter versionamento dos arquivos, que pode ser simples ou até mesmo usar um git interno.
 - quero começar o projeto com um dockerfile rodando localmente para validar a idéia na prórpia <client>.
 - quero reaproveitar muita coisa que já temos no projeto nexa /home/tagore/dev/nexa/ lá tem a UI de um helpcenter que pode ser aproveitada, tem também stripe para pagamento, enfim, analise a fundo o que pode ser aproveitado.
 - veja também o que já temos feito só com a skill na <client>: /home/tagore/dev/<client>/main/packages/docs/
 - minha idéia agora é dar vida para este fluxo, tanto o processo de criação quando a publicação destes arquivos .md em ambiente de help center.
 - como inspiração para este produto tenho o https://www.mintlify.com/
 - muito possívelmente ele se chamará Nexa também, mas a versão 2. vc pode aproveitar todo o pipeline de deploy, etc. se quiser copiar o projeto nexa e apagar o que não precisamos, também vale (toda parte de video, e editor de video, morre neste V2)
 - No futuro quero ter um embeded no saas da <client>/do cliente, e o nexa já tem isso também, para permitir busca na documentação.
 - quero que o cliente deste produto possa ter a documentação toda disponível em um diretório de sua maquina, mas quero manter privada a inteligencia de geração, o grafo dos projetos etc. mas seria ideal que ele possa manter isso na codebase pois é útil para ajudar a IA no trabalho de desenvolvimento do saas, uma alternativa seria criarmos um MCP para que a IA local busque na documentação.