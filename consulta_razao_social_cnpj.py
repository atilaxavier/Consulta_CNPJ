import csv
import time
import requests

# Configurações de arquivos
ARQUIVO_ENTRADA = "cnpjs.csv"  # Substitua pelo nome do seu arquivo de entrada
ARQUIVO_SAIDA = "resultados_cnpjs.csv"

print("Iniciando a consulta dos CNPJs...")

# Abre o arquivo de entrada para leitura e o de saída para escrita
with open(ARQUIVO_ENTRADA, mode="r", encoding="utf-8") as incsv, open(
    ARQUIVO_SAIDA, mode="w", newline="", encoding="utf-8"
) as outcsv:

    leitor = csv.reader(incsv)
    escritor = csv.writer(outcsv, delimiter=",")

    # Escreve o cabeçalho no arquivo de saída
    escritor.writerow(["cnpj", "razao_social"])

    for linha in leitor:
        if not linha:
            continue  # Pula linhas vazias

        # Pega o CNPJ (remove pontos, traços, barras e espaços extras)
        cnpj_bruto = linha[0]
        cnpj = (
            cnpj_bruto.replace(".", "")
            .replace("-", "")
            .replace("/", "")
            .strip()
        )

        # Pula a linha do cabeçalho caso o arquivo de entrada possua uma
        if cnpj.lower() == "cnpj" or not cnpj.isdigit():
            continue

        # Exemplo: https://brasilapi.com.br/api/cnpj/v1/26397010000104
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

        try:
            resposta = requests.get(url, timeout=10)

            if resposta.status_code == 200:
                dados = resposta.json()
                razao_social = dados.get("razao_social", "Não encontrada")
                escritor.writerow([cnpj, razao_social])
                print(f"CNPJ {cnpj}: Sucesso ({razao_social})")

            elif resposta.status_code == 404:
                escritor.writerow([cnpj, "CNPJ nao encontrado"])
                print(f"CNPJ {cnpj}: Não encontrado (404)")

            else:
                escritor.writerow([cnpj, f"Erro status {resposta.status_code}"])
                print(f"CNPJ {cnpj}: Erro HTTP {resposta.status_code}")

        except requests.exceptions.RequestException as e:
            escritor.writerow([cnpj, "Erro de conexao"])
            print(f"CNPJ {cnpj}: Falha de conexão")

        # Pausa leve para respeitar os limites de requisições por minuto da API
        time.sleep(0.5)

print(f"\nProcesso concluído! Os resultados foram salvos em: {ARQUIVO_SAIDA}")
