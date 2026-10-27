import requests

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
BASE_ID = "appjM48jtF1tccYVq".strip()
NOME_TABELA = "Inventario"

def verificar_estoque_robusto():
    url = f"https://api.airtable.com/v0/{BASE_ID}/{NOME_TABELA}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    todos_os_registros = []
    offset = None
    
    # 1. Tratamento de Paginação (Garante a leitura de todo o catálogo)
    while True:
        params = {"offset": offset} if offset else {}
        try:
            resposta = requests.get(url, headers=headers, params=params)
            dados = resposta.json()
            
            if 'error' in dados:
                return {"sucesso": False, "erro": dados['error']}
            
            records = dados.get('records', [])
            todos_os_registros.extend(records)
            
            offset = dados.get('offset')
            if not offset:
                break
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    # 2. Segmentação por Categoria e Tratamento de Dados
    alertas = {"Bebidas": [], "Cosméticos": [], "Insumos/Outros": []}
    
    for registro in todos_os_registros:
        campos = registro.get('fields', {})
        produto = campos.get('Produto', 'Produto Sem Nome')
        categoria = campos.get('Categoria', 'Outros')
        
        # Conversão segura de dados
        raw_qtd = campos.get('Qtd Atual')
        raw_min = campos.get('Estoque Minimo')
        
        try:
            qtd_atual = float(raw_qtd) if raw_qtd is not None else 0.0
            estoque_minimo = float(raw_min) if raw_min is not None else 0.0
        except (ValueError, TypeError):
            continue

        if qtd_atual < estoque_minimo:
            item = {
                "produto": produto,
                "qtd_atual": qtd_atual,
                "estoque_minimo": estoque_minimo,
                "comprar": estoque_minimo - qtd_atual
            }
            
            if "Bebida" in categoria:
                alertas["Bebidas"].append(item)
            elif "Cosmético" in categoria:
                alertas["Cosméticos"].append(item)
            else:
                alertas["Insumos/Outros"].append(item)

    return {"sucesso": True, "alertas": alertas}

if __name__ == "__main__":
    print("="*60)
    print("⚙️ [COO V2 - PROD] Varredura Geral do Estoque no Airtable...\n")
    
    resultado = verificar_estoque_robusto()
    
    if not resultado["sucesso"]:
        print(f"❌ Falha no relatório: {resultado['erro']}")
    else:
        alertas = resultado["alertas"]
        tem_ruptura = any(len(v) > 0 for v in alertas.values())
        
        if not tem_ruptura:
            print("✅ Estoque seguro no Bar Raio do Sol e na Fillara Cosméticos.")
        else:
            print("🚨 RELATÓRIO DE RUPTURA ORGANIZADO POR OPERAÇÃO:\n")
            
            if alertas["Bebidas"]:
                print("🍺 [BAR RAIO DO SOL]")
                for item in alertas["Bebidas"]:
                    print(f"  • {item['produto']}: Atual = {item['qtd_atual']} | Mínimo = {item['estoque_minimo']} (Comprar +{item['comprar']})")
            
            if alertas["Cosméticos"]:
                print("\n💄 [FILLARA COSMÉTICOS]")
                for item in alertas["Cosméticos"]:
                    print(f"  • {item['produto']}: Atual = {item['qtd_atual']} | Mínimo = {item['estoque_minimo']} (Comprar +{item['comprar']})")
                    
            if alertas["Insumos/Outros"]:
                print("\n📦 [INSUMOS E DIVERSOS]")
                for item in alertas["Insumos/Outros"]:
                    print(f"  • {item['produto']}: Atual = {item['qtd_atual']} | Mínimo = {item['estoque_minimo']} (Comprar +{item['comprar']})")
    print("="*60)