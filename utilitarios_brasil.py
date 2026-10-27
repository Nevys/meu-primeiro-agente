import requests

BASE_URL = "https://brasilapi.com.br/api"

def buscar_cep(cep: str):
    """
    Usado pelo CSO/CRM: Valida e retorna o endereço completo a partir do CEP.
    """
    cep_limpo = str(cep).replace("-", "").replace(".", "").strip()
    url = f"{BASE_URL}/cep/v2/{cep_limpo}"
    
    try:
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            dados = resposta.json()
            return {
                "sucesso": True,
                "logradouro": dados.get("street", "N/A"),
                "bairro": dados.get("neighborhood", "N/A"),
                "cidade": dados.get("city", "N/A"),
                "estado": dados.get("state", "N/A")
            }
        return {"sucesso": False, "erro": "CEP não encontrado."}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def buscar_cnpj(cnpj: str):
    """
    Usado pelo CPO/CFO: Valida situação cadastral de fornecedores ou do seu MEI.
    """
    cnpj_limpo = str(cnpj).replace(".", "").replace("/", "").replace("-", "").strip()
    url = f"{BASE_URL}/cnpj/v1/{cnpj_limpo}"
    
    try:
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            dados = resposta.json()
            return {
                "sucesso": True,
                "razao_social": dados.get("razao_social"),
                "nome_fantasia": dados.get("nome_fantasia"),
                "situacao": dados.get("descricao_situacao_cadastral"),
                "cidade": dados.get("municipio"),
                "uf": dados.get("uf")
            }
        return {"sucesso": False, "erro": "CNPJ não localizado ou inválido."}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def buscar_preco_fipe(codigo_fipe: str):
    """
    Usado pelo CFO: Consulta o valor atualizado de um veículo na Tabela FIPE.
    """
    url = f"{BASE_URL}/fipe/preco/v1/{codigo_fipe.strip()}"
    
    try:
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            dados = resposta.json()
            if dados:
                item = dados[0]  # Pega a referência mais recente
                return {
                    "sucesso": True,
                    "marca": item.get("marca"),
                    "modelo": item.get("modelo"),
                    "ano": item.get("anoModelo"),
                    "valor": item.get("valor"),
                    "combustivel": item.get("combustivel")
                }
        return {"sucesso": False, "erro": "Código FIPE não localizado."}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# =====================================================================
# TESTE DAS INTEGRACÕES
# =====================================================================
if __name__ == "__main__":
    print("="*60)
    print("🇧🇷 [UTILITÁRIOS BRASILAPI] Testando serviços públicos...\n")

    # 1. Teste de CEP (Itabuna/BA)
    print("📍 1. CONSULTA DE CEP:")
    resultado_cep = buscar_cep("45600-000")
    print(resultado_cep)
    print("-" * 50)

    # 2. Teste de FIPE (Exemplo: Código FIPE de veículo comercial)
    print("🚗 2. CONSULTA TABELA FIPE:")
    resultado_fipe = buscar_preco_fipe("004001-0") # Exemplo código FIPE
    print(resultado_fipe)
    print("="*60)