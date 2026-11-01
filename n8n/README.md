# Integração n8n

O fluxo usa `Webhook → HTTP Request → Respond to Webhook`. O JSON enviado é preservado até a API e o código HTTP dela volta ao solicitante. Uma entrada inválida retorna 422 também pelo n8n, sem virar uma resposta 200 de sucesso aparente.

## Runtime local

O workflow tem ID estável `portfolioTicket1` e chama `http://ticket-triage:8001/predict`. O serviço `ticket-triage` e o n8n devem compartilhar a rede Compose. O arquivo não acessa `$env`, não possui credenciais e é importado como inativo.

Este repositório não inclui um arquivo Compose para a integração. Para usar os comandos abaixo, configure um ambiente com os dois serviços na mesma rede, monte este diretório em `/workflows/ticket-triage:ro` e publique o n8n apenas em `127.0.0.1:5678`. Com os serviços iniciados, execute na pasta do seu Compose:

```powershell
docker compose exec n8n n8n import:workflow --input=/workflows/ticket-triage/ticket-triage.json
docker compose exec n8n n8n publish:workflow --id=portfolioTicket1
docker compose restart n8n
```

O restart é necessário porque esses comandos alteram o banco do n8n; o processo já iniciado precisa registrar o webhook publicado. Isso publica o fluxo **na instância local**, sem hospedar nada na internet. Para interromper o webhook, use `n8n unpublish:workflow --id=portfolioTicket1` no mesmo serviço e reinicie-o.

## Teste real

Depois que o n8n estiver pronto, execute na raiz deste projeto:

```powershell
python n8n/verify_webhook.py --base-url http://127.0.0.1:5678 --report n8n/validation.json
```

O script usa somente a biblioteca padrão do Python e faz três requisições HTTP reais ao n8n: previsão válida, texto vazio e campo extra. Ele exige a classe esperada, os campos do modelo e os códigos 422 da API. Não usa mocks nem executa o classificador diretamente. Uma previsão sintética é acrescentada ao histórico da API.

**Validação realizada:** importação e publicação na imagem `docker.n8n.io/n8nio/n8n:2.44.7`, com API em contêiner e três casos aprovados. O [registro da execução HTTP](validation.json) contém horários, status e versão do modelo. A validação percorreu o webhook publicado, o HTTP Request e a resposta final. A [conferência do runtime](runtime-validation.json) também registra os três estados `success` no banco do n8n e o modo externo do runner.

Para testar manualmente:

```powershell
$body = @{text='Minha senha foi recusada e não consigo fazer login'} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:5678/webhook/ticket-triage -Method Post -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

`/webhook-test/ticket-triage` é outra rota: funciona somente enquanto o editor está em **Listen for Test Event**. A validação automatizada usa `/webhook/ticket-triage`, que exige workflow publicado. `n8n execute --id=...` não exercita a entrada HTTP do Webhook e não substitui este teste.

## Fora do Compose

Se n8n e API rodam no mesmo host, altere a URL do nó HTTP para `http://127.0.0.1:8001/predict`. Com n8n no Docker Desktop e API no host, use `http://host.docker.internal:8001/predict` e uma interface de escuta acessível ao contêiner. Se renomear o serviço Compose, atualize o hostname no workflow. Não é necessário liberar acesso a variáveis de ambiente dos nós.

## Referências verificadas

- [Server CLI: importação, publicação e reinício](https://docs.n8n.io/hosting/cli-commands/).
- [Webhook: URLs de teste e de produção](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/).
- [HTTP Request: resposta completa e Never Error](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).
- [Respond to Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/).

`Never Error` permite tratar respostas HTTP 4xx/5xx e devolvê-las ao solicitante. Falhas de transporte, como DNS indisponível ou timeout, continuam sendo falhas de execução do workflow.

