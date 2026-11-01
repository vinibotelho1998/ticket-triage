# Model card

- **Tarefa:** classificar um chamado curto em português entre acesso, cancelamento, cobrança e erro técnico.
- **Modelo:** TF-IDF de unigramas/bigramas, máximo de 10 mil termos; regressão logística com `C=3`, pesos de classe balanceados e seed 42.
- **Dados:** 192 exemplos sintéticos, 48 cenários. Ver [data/DATA_CARD.md](data/DATA_CARD.md).
- **Divisão:** 75%/25% dos cenários, estratificada por classe. As variações de um cenário não atravessam a partição. Nenhum ajuste do vocabulário utiliza o holdout.
- **Baseline:** classe mais frequente no treino. O empate é resolvido pela implementação do scikit-learn; seu macro-F1 é 0,1 neste dataset balanceado.
- **Métrica principal:** macro-F1; o relatório também inclui precisão/recall por classe, support, confusão e erros individuais.
- **Artefato:** `var/model.joblib`, ignorado pelo Git e reproduzível com o comando de treinamento e as dependências registradas.
- **Versão:** hash da identidade do pipeline, seed, SHA-256 do CSV e versão do scikit-learn. Não é assinatura criptográfica do arquivo binário nem substitui verificação de procedência.
- **Score:** saída não calibrada de `predict_proba`. Não usar como certeza, SLA ou critério automático de decisões sensíveis.
- **Uso pretendido:** demonstração de pipeline supervisionado, API e auditoria de correções.
- **Fora de escopo:** decisões autônomas sobre clientes, roteamento de assuntos não treinados, mensagens com múltiplos temas e avaliação de satisfação.

O holdout permaneceu com a configuração inicial; não houve seleção de modelo por seus resultados. Ainda assim, os exemplos são próximos entre si e produzidos pelo mesmo gerador, então a avaliação é limitada. Um próximo experimento precisa reservar dados novos antes de alterar o pipeline. Feedback da API não é incorporado automaticamente.

