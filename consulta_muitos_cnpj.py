import csv
import time
import argparse
import pandas as pd
import requests

DELAY_PADRAO = 1.5
TEMPO_ESPERA_BLOQUEIO = 60  # Tempo em segundos para esperar após o erro 429

def main():
    # Definir argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="Script para consultar dados de múltiplos CNPJs via API Brasil"
    )
    parser.add_argument(
        "-i", "--input",
        default="cnpjs.csv",
        help="Arquivo de entrada com CNPJs (padrão: cnpjs.csv)"
    )
    parser.add_argument(
        "-o", "--output",
        default="resultados_completos_cnpjs.csv",
        help="Arquivo de saída para resultados (padrão: resultados_completos_cnpjs.csv)"
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["razao_social", "all"],
        default="razao_social",
        help="Modo de operação: 'razao_social' (apenas razão social) ou 'all' (todos os dados). Padrão: razao_social"
    )

    args = parser.parse_args()

    ARQUIVO_ENTRADA = args.input
    ARQUIVO_SAIDA = args.output
    modo = args.mode

    print(f"Iniciando processamento em lote com tratamento estrito de Rate Limit (429)...")
    print(f"Arquivo de entrada: {ARQUIVO_ENTRADA}")
    print(f"Arquivo de saída: {ARQUIVO_SAIDA}")
    print(f"Modo: {modo}\n")

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
                
                # Aplica o filtro conforme o modo
                if modo == "razao_social":
                    # Mantém apenas CNPJ e razao_social
                    dados_filtrados = {
                        "cnpj": dados_achatados.get("cnpj", ""),
                        "razao_social": dados_achatados.get("razao_social", "")
                    }
                    lista_resultados.append(dados_filtrados)
                else:  # modo == "all"
                    # Salva todos os dados
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

if __name__ == "__main__":
    main()
