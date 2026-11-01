"""Gera exemplos totalmente sintéticos; não representa demanda de clientes reais."""

import argparse
import csv
import random
from pathlib import Path

SCENARIOS = {
    "acesso": [
        "Não consigo entrar na conta, minha senha foi recusada",
        "Esqueci a senha e preciso recuperar meu acesso",
        "O código de autenticação não chegou para fazer login",
        "Minha conta está bloqueada e não consigo acessar",
        "Preciso trocar o email usado no login da conta",
        "A senha nova não funciona para entrar no sistema",
        "O link de recuperação de senha expirou",
        "Perdi o autenticador e não consigo fazer login",
        "Quero redefinir a senha para acessar a conta",
        "A confirmação de login por email não funciona",
        "O acesso foi negado mesmo com a senha correta",
        "Não recebo o código para desbloquear minha conta",
    ],
    "cancelamento": [
        "Quero cancelar minha assinatura e encerrar o plano",
        "Como faço o cancelamento da assinatura mensal",
        "Não quero renovar meu plano, desejo cancelar",
        "Preciso encerrar a assinatura antes da renovação",
        "Quero parar de usar o serviço e cancelar o contrato",
        "Solicito cancelamento definitivo do meu plano",
        "Desejo desativar a renovação automática da assinatura",
        "Gostaria de encerrar meu contrato de assinatura",
        "Podem cancelar o plano anual da minha conta",
        "Quero confirmar o encerramento da minha assinatura",
        "Qual é o procedimento para cancelar o serviço",
        "Meu pedido de cancelamento do plano não foi concluído",
    ],
    "cobranca": [
        "A cobrança veio duplicada na fatura do cartão",
        "Preciso da segunda via do boleto de pagamento",
        "O valor cobrado na fatura está errado",
        "Meu pagamento foi feito mas o boleto está em aberto",
        "Quero uma nota fiscal referente ao pagamento",
        "A fatura mostra uma cobrança que não reconheço",
        "Como atualizar o cartão usado no pagamento",
        "Preciso de estorno de uma cobrança duplicada",
        "O boleto venceu e preciso pagar a fatura",
        "O pagamento do cartão foi recusado na cobrança",
        "Não encontro o recibo do pagamento da mensalidade",
        "Foi cobrado um valor maior do que consta na fatura",
    ],
    "erro_tecnico": [
        "O aplicativo trava quando tento exportar o relatório",
        "A tela fica branca ao abrir o painel do sistema",
        "O sistema retorna erro 500 ao salvar um arquivo",
        "O aplicativo fecha sozinho ao carregar uma imagem",
        "O botão de exportar não funciona e aparece um erro",
        "O painel está lento e o relatório não carrega",
        "Recebo uma mensagem de erro ao enviar arquivos",
        "A página trava e não consigo salvar as alterações",
        "O relatório exportado está vazio por um erro do sistema",
        "O aplicativo apresenta falha ao abrir a configuração",
        "A tela do painel desaparece depois da atualização",
        "O sistema fica carregando sem concluir a operação",
    ],
}

PREFIXES = ("Olá, ", "Bom dia! ", "Preciso de ajuda: ", "")
SUFFIXES = (". Podem verificar?", ". Isso aconteceu hoje.", ". Aguardo orientação.", ".")


def generate(output: Path, seed: int = 42) -> int:
    rng = random.Random(seed)
    rows = []
    for label, scenarios in SCENARIOS.items():
        for index, message in enumerate(scenarios):
            for variation in range(4):
                rows.append({
                    "id": f"{label}-{index:02d}-{variation}",
                    "scenario_id": f"{label}-{index:02d}",
                    "text": PREFIXES[variation] + message + SUFFIXES[variation],
                    "label": label,
                    "source": "synthetic-template-v1",
                })
    rng.shuffle(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/tickets.csv"))
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    print(f"{generate(arguments.output, arguments.seed)} exemplos sintéticos em {arguments.output}")

