import csv
import time
import requests

ARQUIVO_ENTRADA = "cnpjs.csv"
ARQUIVO_SAIDA = "resultados_cnpjs.csv"

# Configurações de controle de requisições
DELAY_PADRAO = 0.6  # Tempo de espera normal entre chamadas (em segundos)
TEMPO_ESPERA_BLOQUEIO = 60  # Tempo para esperar caso seja bloqueado por taxa


def consultar_cnpj_com_reentry(cnpj):
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

    while True:
        try:
            resposta = requests.get(url, timeout=15)

            if resposta.status_code == 200:
                dados = resposta.json()
                return dados.get("razao_social", "Razão Social não encontrada")

            elif resposta.status_code == 404:
                return "CNPJ não encontrado na base"

            elif resposta.status_code == 429:
                print(
                    f"\n[!] Limite de requisições atingido. Aguardando {TEMPO_ESPERA_BLOQUEIO} segundos para liberar o IP..."
                )
                time.sleep(TEMPO_ESPERA_BLOQUEIO)
                continue  # Tenta o mesmo CNPJ novamente após a pausa

            else:
                return f"Erro HTTP {resposta.status_code}"

        except requests.exceptions.RequestException:
            print(
                f"\n[!] Falha de conexão ao consultar {cnpj}. Aguardando 5s antes de tentar de novo..."
            )
            time.sleep(5)
            continue


print("Iniciando processamento em lote...")

with open(ARQUIVO_ENTRADA, mode="r", encoding="utf-8") as incsv, open(
    ARQUIVO_SAIDA, mode="w", newline="", encoding="utf-8"
) as outcsv:

    leitor = csv.reader(incsv)
    escritor = csv.writer(outcsv, delimiter=",")

    escritor.writerow(["cnpj", "razao_social"])

    contador = 0

    for linha in leitor:
        if not linha:
            continue

        # Limpeza rigorosa do input
        cnpj_bruto = linha[0]
        cnpj = "".join(filter(str.isdigit, cnpj_bruto))

        if not cnpj or len(cnpj) != 14:
            # Ignora cabeçalhos textuais ou registros sabidamente inválidos
            continue

        razao_social = consultar_cnpj_com_reentry(cnpj)

        escritor.writerow([cnpj, razao_social])
        outcsv.flush()  # Força a gravação imediata no HD (evita perder dados se o script cair)

        contador += 1
        if contador % 10 == 0:
            print(f">> {contador} CNPJs processados com sucesso.")

        time.sleep(DELAY_PADRAO)

print(f"\n[Sucesso] Processo finalizado. Arquivo gerado: {ARQUIVO_SAIDA}")
