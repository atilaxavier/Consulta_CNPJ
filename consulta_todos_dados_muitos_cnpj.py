import csv
import time
import pandas as pd
import requests

ARQUIVO_ENTRADA = "cnpjs.csv"
ARQUIVO_SAIDA = "resultados_completos_cnpjs.csv"

DELAY_PADRAO = 0.6
TEMPO_ESPERA_BLOQUEIO = 60  # Tempo em segundos para esperar após o erro 429

print("Iniciando processamento em lote com tratamento estrito de Rate Limit (429)...")

lista_resultados = []
contador = 0

with open(ARQUIVO_ENTRADA, mode="r", encoding="utf-8") as incsv:
    leitor = csv.reader(incsv)

    for linha in leitor:
        if not linha:
            continue

        cnpj_bruto = linha[0]
        cnpj = "".join(filter(str.isdigit, cnpj_bruto))

        if not cnpj or len(cnpj) != 14:
            continue

        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        
        # Este bloco garante que o script SÓ passa para o próximo CNPJ quando este terminar com sucesso ou erro definitivo (como 404)
        sucesso_ou_erro_definitivo = False
        dados_json = None

        while not sucesso_ou_erro_definitivo:
            try:
                resposta = requests.get(url, timeout=15)

                if resposta.status_code == 200:
                    dados_json = resposta.json()
                    sucesso_ou_erro_definitivo = True
                    
                elif resposta.status_code == 404:
                    dados_json = {"cnpj": cnpj, "status_registro": "CNPJ não encontrado"}
                    sucesso_ou_erro_definitivo = True
                    
                elif resposta.status_code == 429:
                    # TRATAMENTO DO BLOQUEIO: Não muda o estado da variável, forçando o 'while' a repetir o MESMO CNPJ
                    print(f"\n[!] Rate limit (Erro 429) atingido no CNPJ {cnpj}.")
                    print(f"Aguardando {TEMPO_ESPERA_BLOQUEIO} segundos para tentar o MESMO CNPJ novamente...")
                    time.sleep(TEMPO_ESPERA_BLOQUEIO)
                    
                else:
                    dados_json = {"cnpj": cnpj, "status_registro": f"Erro HTTP {resposta.status_code}"}
                    sucesso_ou_erro_definitivo = True

            except requests.exceptions.RequestException as e:
                print(f"\n[!] Falha de conexão no CNPJ {cnpj}. Erro: {e}. Aguardando 5s para tentar de novo...")
                time.sleep(5)

        # Processa e achata o JSON coletado com sucesso
        if dados_json:
            dados_achatados = pd.json_normalize(dados_json).to_dict(orient="records")[0]
            lista_resultados.append(dados_achatados)

        contador += 1
        if contador % 10 == 0:
            print(f">> {contador} CNPJs processados.")

        time.sleep(DELAY_PADRAO)

# Fase de salvamento dos dados
if lista_resultados:
    print("\nConstruindo o arquivo consolidado...")
    df_final = pd.DataFrame(lista_resultados)

    # Reorganiza para garantir que a coluna 'cnpj' seja sempre a primeira
    if "cnpj" in df_final.columns:
        colunas = ["cnpj"] + [col for col in df_final.columns if col != "cnpj"]
        df_final = df_final[colunas]

    # Salva garantindo compatibilidade de acentos no Excel através do 'utf-8-sig'
    df_final.to_csv(ARQUIVO_SAIDA, index=False, sep=",", encoding="utf-8-sig")
    print(f"[Sucesso] Arquivo gerado com {len(df_final.columns)} colunas em: {ARQUIVO_SAIDA}")
else:
    print("\n[Erro] Nenhuma informação foi coletada.")
