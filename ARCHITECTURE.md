# Arquitetura

`CSV → divisão por cenário → TF-IDF → regressão logística → artefato joblib + relatório`

`HTTP /predict → validação Pydantic → modelo em memória → transação SQLite → resposta`

`PUT feedback → validação da classe → vínculo com predição existente → upsert SQLite`

O módulo `generate` define a procedência dos dados. `train` é independente da API e produz um artefato com versão derivada de dataset, configuração e versão da biblioteca. `api` carrega um modelo na inicialização, mantém handlers síncronos para trabalho bloqueante e expõe o contrato OpenAPI. `store` abre uma conexão curta por operação, usa WAL, foreign keys, consultas parametrizadas e fecha a conexão após commit ou rollback.

O escopo é um processo local e uma base SQLite. Não há fila, retreinamento automático nem substituição de modelo em uma API já iniciada. A memória do modelo não é compartilhada entre processos; cada worker carregaria sua própria cópia. A escrita no histórico faz parte do sucesso de `/predict`: se ela falhar, a requisição falha.

O texto original só passa pela memória durante a predição. O histórico não é um log de conteúdo e não permite reconstituir um conjunto supervisionado. Identificadores aleatórios ligam correções humanas à versão do modelo que produziu a resposta. PUT do mesmo feedback atualiza a linha existente.

O n8n é uma borda opcional. Ele não implementa o classificador e não é necessário para treinar, testar ou usar a API. A chamada de classificação não é idempotente: repetir POST gera uma nova entrada de histórico. Isso representa solicitações distintas e está separado da idempotência do PUT de feedback.

