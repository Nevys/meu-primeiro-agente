import os
import requests

# Agora o import os está aqui e vai funcionar
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

def gerar_ordens_de_compra():
    return "✅ Ordem de compra verificada pelo CPO."

def buscar_fornecedores():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Fornecedores"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    try:
        resposta = requests.get(url, headers=headers)
        dados = resposta.json()
        if 'error' in dados:
            return {"sucesso": False, "erro": dados['error']}
        fornecedores = []
        for reg in dados.get('records', []):
            campos = reg.get('fields', {})
            raw_preco = campos.get('Preco Atual') or campos.get('Preço Atual')
            try:
                preco = float(raw_preco) if raw_preco is not None else 0.0
            except (ValueError, TypeError):
                preco = 0.0
            fornecedores.append({
                "empresa": campos.get('Empresa', 'Desconhecido'),
                "produto": campos.get('Produto Fornecido', 'Desconhecido'),
                "preco": preco,
                "contato": campos.get('Telefone_WhatsApp', campos.get('Telefone/WhatsApp', 'Não informado'))
            })
        return {"sucesso": True, "fornecedores": fornecedores}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def prospectar_fornecedores_web(produto, categoria):
    """Realiza varredura na internet em tempo real."""
    termo = f"distribuidor atacado {produto} {categoria} Bahia"
    try:
        resultados = []
        with DDGS() as ddgs:
            for r in ddgs.text(termo, max_results=2):
                resultados.append({
                    "titulo": r.get('title'),
                    "link": r.get('href'),
                    "resumo": r.get('body')
                })
        return {"sucesso": True, "resultados": resultados}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def gerar_ordens_de_compra():
    print("="*60)
    print("🛍️ [CPO Virtual V3] Cotando fornecedores e prospectando na Web...\n")
    
    resultado_coo = verificar_estoque_robusto()
    if not resultado_coo["sucesso"]:
        print(f"❌ Erro ao consultar estoque pelo COO: {resultado_coo['erro']}")
        return
        
    alertas = resultado_coo["alertas"]
    itens_com_categoria = []
    for cat in ["Bebidas", "Cosméticos", "Produtos Eróticos", "Insumos/Outros"]:
        for item in alertas.get(cat, []):
            item["categoria_macro"] = cat
            itens_com_categoria.append(item)
    
    if not itens_com_categoria:
        print("✅ Nenhum produto com necessidade de reposição no momento.")
        print("="*60)
        return

    resultado_forn = buscar_fornecedores()
    if not resultado_forn["sucesso"]:
        print(f"❌ Erro ao acessar Airtable: {resultado_forn['erro']}")
        return
        
    fornecedores = resultado_forn["fornecedores"]
    investimento_total = 0.0
    
    for item in itens_com_categoria:
        nome_prod = item["produto"]
        qtd_comprar = item["comprar"]
        cat_macro = item["categoria_macro"]
        
        forn_encontrado = None
        for f in fornecedores:
            if f["produto"].lower() in nome_prod.lower() or nome_prod.lower() in f["produto"].lower():
                forn_encontrado = f
                break
                
        if forn_encontrado:
            custo_item = qtd_comprar * forn_encontrado["preco"]
            investimento_total += custo_item
            print(f"📦 Produto: {nome_prod} ({cat_macro})")
            print(f"   • Quantidade a Comprar: {qtd_comprar}")
            print(f"   • Fornecedor Cadastrado: {forn_encontrado['empresa']}")
            print(f"   • Custo Unitário: R$ {forn_encontrado['preco']:.2f}")
            print(f"   • Custo Total: R$ {custo_item:.2f}")
            print(f"   • Contato: {forn_encontrado['contato']}")
            print("-" * 50)
        else:
            print(f"⚠️ Produto: {nome_prod} [{cat_macro}] (Reposição: +{qtd_comprar})")
            print("   • Status: Sem fornecedor cadastrado na aba 'Fornecedores'.")
            print("   🌐 Realizando Varredura de Fornecedores na Web...")
            
            res_web = prospectar_fornecedores_web(nome_prod, cat_macro)
            if res_web["sucesso"] and res_web["resultados"]:
                print("   💡 [FORNECEDORES / ATACADISTAS ENCONTRADOS NA INTERNET]:")
                for site in res_web["resultados"]:
                    print(f"      🔗 {site['titulo']}")
                    print(f"         Link: {site['link']}")
                    print(f"         Resumo: {site['resumo'][:120]}...")
            else:
                print("      ⚠️ Nenhum site localizado na busca web.")
            print("-" * 50)
            
    print(f"\n💰 ORÇAMENTO TOTAL CONFIRMADO: R$ {investimento_total:.2f}")
    print("="*60)

if __name__ == "__main__":
    gerar_ordens_de_compra()