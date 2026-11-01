# Dados

`tickets.csv` foi gerado integralmente pelo código `src/ticket_triage/generate.py`, com seed 42. Não contém mensagens de clientes, dados raspados, informações pessoais ou conteúdo de uma empresa. As frases e seus rótulos foram escritos para esta demonstração.

Cada uma das quatro classes tem 12 cenários e quatro variações por cenário, totalizando 48 exemplos por classe. Variações mudam somente saudação e fechamento. `scenario_id` identifica esse parentesco e é a unidade da divisão treino/teste. `source` registra `synthetic-template-v1`.

Regeneração: `python -m ticket_triage.generate --seed 42`. O mesmo gerador e seed produzem os mesmos bytes. O treino rejeita IDs duplicados, textos idênticos normalizados, rótulos desconhecidos e cenários com classes conflitantes.

Esse material é propositalmente pequeno e artificial. Ele não demonstra cobertura da língua portuguesa, dos estilos de clientes ou do desequilíbrio de classes que ocorre em atendimento real. Números de avaliação devem ser apresentados junto dessa limitação.

