import csv
import time
import pandas as pd
import requests

ARQUIVO_ENTRADA = "cnpjs.csv"
ARQUIVO_SAIDA = "resultados_completos_cnpjs.csv"

DELAY_PADRAO = 0.6
TEMPO_ESPERA_BLOQUEIO = 60


def consultar_cnpj_completo(cnpj):
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

    while True:
        try:
            resposta = requests.get(url, timeout=15)

            if resposta.status_code == 200:
                # Retorna o dicionário completo com todas as chaves da API
                return resposta.json()

            elif resposta.status_code == 404:
                return {"cnpj": cnpj, "status_registro": "CNPJ não encontrado"}

            elif resposta.status_code == 429:
                print(
                    f"\n[!] Rate limit atingido. Aguardando {TEMPO_ESPERA_BLOQUEIO}s..."
                )
                time.sleep(TEMPO_ESPERA_BLOQUEIO)
                continue

            else:
                return {
                    "cnpj": cnpj,
                    "status_registro": f"Erro HTTP {resposta.status_code}",
                }

        except requests.exceptions.RequestException:
            print(
                f"\n[!] Falha de conexão ao consultar {cnpj}. Aguardando 5s..."
            )
            time.sleep(5)
            continue


print("Iniciando processamento em lote com extração total de dados...")

lista_resultados = []
contador = 0

# Fase 1: Coleta e processamento dos dados na memória
with open(ARQUIVO_ENTRADA, mode="r", encoding="utf-8") as incsv:
    leitor = csv.reader(incsv)

    for i, linha in enumerate(leitor):
        if not linha:
            continue

        cnpj_bruto = linha[0]
        cnpj = "".join(filter(str.isdigit, cnpj_bruto))

        if not cnpj or len(cnpj) != 14:
            continue

        dados_json = consultar_cnpj_completo(cnpj)

        # Utiliza o pandas para transformar sub-listas (como sócios/CNAEs) em texto legível dentro da linha
        # Isso evita que o CSV quebre linhas incorretamente
        dados_achatados = pd.json_normalize(dados_json).to_dict(
            orient="records"
        )[0]

        lista_resultados.append(dados_achatados)

        contador += 1
        if contador % 10 == 0:
            print(f">> {contador} CNPJs consultados...")

        time.sleep(DELAY_PADRAO)

# Fase 2: Construção dinâmica do CSV com todas as colunas descobertas
if lista_resultados:
    print("\nFormatando e salvando o arquivo final...")

    # Transforma a lista de dicionários em um DataFrame do Pandas
    # Ele automaticamente cria colunas para todas as chaves diferentes encontradas
    df_final = pd.DataFrame(lista_resultados)

    # Garante que a coluna CNPJ original seja a primeira do arquivo
    if "cnpj" in df_final.columns:
        colunas = ["cnpj"] + [col for col in df_final.columns if col != "cnpj"]
        df_final = df_final[colunas]

    # Salva em CSV usando vírgula como separador
    df_final.to_csv(ARQUIVO_SAIDA, index=False, sep=",", encoding="utf-8-sig")
    print(
        f"[Sucesso] Processo finalizado! Arquivo gerado com {len(df_final.columns)} colunas: {ARQUIVO_SAIDA}"
    )
else:
    print("\n[Erro] Nenhum dado válido foi processado.")
