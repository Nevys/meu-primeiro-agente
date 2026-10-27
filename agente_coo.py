import os
import requests
import time

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

def verificar_estoque_robusto():
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Inventário" 
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200: return f"⚠️ Erro ao acessar o Inventário: {res.text}"
        
        records = res.json().get("records", [])
        alertas, total_itens = [], 0
        
        for record in records:
            fields = record.get("fields", {})
            produto = str(fields.get("Produto", "Item sem nome"))
            unidade = str(fields.get("Unidade", "Geral"))
            try:
                qtd_atual = float(fields.get("Quantidade", 0))
                estoque_min = float(fields.get("Estoque Mínimo", 5)) 
            except (ValueError, TypeError): continue
                
            total_itens += 1
            if qtd_atual <= estoque_min:
                alertas.append(f"• **{produto}** ({unidade}): Restam {qtd_atual:.0f} unid. (Mín: {estoque_min:.0f})")
                
        if not alertas: return f"✅ **Auditoria do COO Concluída:** {total_itens} itens seguros!"
        return "🚨 **ALERTA DE RUPTURA DE ESTOQUE** 🚨\n\n" + "\n".join(alertas)
    except Exception as e: return f"❌ Erro interno COO: {e}"

def sincronizar_contagem_fisica(itens_contados):
    """Atualiza quantidades de itens existentes ou cria novos registros."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Inventário"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    try:
        res_get = requests.get(url, headers=headers)
        registros_atuais = res_get.json().get('records', [])
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao consultar Airtable: {e}"}

    mapa_produtos = {r['fields'].get('Produto', '').lower().strip(): r['id'] for r in registros_atuais}
    
    atualizacoes, criacoes = [], []
    
    for item in itens_contados:
        nome_prod = str(item.get("produto", "")).strip()
        qtd = float(item.get("quantidade", 0))
        local = str(item.get("local", "Geral"))
        
        record_id = None
        for prod_existente, rid in mapa_produtos.items():
            if prod_existente in nome_prod.lower() or nome_prod.lower() in prod_existente:
                record_id = rid
                break
                
        if record_id:
            atualizacoes.append({"id": record_id, "fields": {"Quantidade": qtd, "Local": local}})
        else:
            criacoes.append({"fields": {"Produto": nome_prod, "Quantidade": qtd, "Local": local, "Unidade": "Bar Raio do Sol"}})

    total_sucesso = 0
    
    for i in range(0, len(atualizacoes), 10):
        lote = atualizacoes[i:i+10]
        requests.patch(url, headers=headers, json={"records": lote})
        total_sucesso += len(lote)
        
    for i in range(0, len(criacoes), 10):
        lote = criacoes[i:i+10]
        requests.post(url, headers=headers, json={"records": lote})
        total_sucesso += len(lote)

    return {"sucesso": True, "mensagem": f"{total_sucesso} produtos sincronizados com sucesso (Físico vs Airtable)."}