import requests
from datetime import datetime
from agente_ia import gerar_script_vendas_whatsapp, gerar_insights_cmo

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
BASE_ID = "appjM48jtF1tccYVq".strip()
TABELA_CRM = "CRM"

def buscar_clientes_crm():
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABELA_CRM}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        resposta = requests.get(url, headers=headers)
        dados = resposta.json()
        
        if 'error' in dados:
            return {"sucesso": False, "erro": dados['error']}
            
        clientes = []
        for reg in dados.get('records', []):
            campos = reg.get('fields', {})
            clientes.append({
                "nome": campos.get('Nome Cliente', 'Cliente'),
                "produto": campos.get('Produto Comprado', 'Produto'),
                "data_compra": campos.get('Data Compra', 'N/A'),
                "alerta_recompra": campos.get('Alerta Recompra', 'N/A')
            })
        return {"sucesso": True, "clientes": clientes}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def executar_radar_vendas_e_crm():
    print("="*60)
    print("🚀 [CMO / CSO Virtual + IA Gemini] Analisando CRM e engajamento...\n")
    
    resultado = buscar_clientes_crm()
    if not resultado["sucesso"]:
        print(f"❌ Erro ao consultar a aba CRM: {resultado['erro']}")
        return
        
    clientes = resultado["clientes"]
    if not clientes:
        print("⚠️ Nenhum cliente cadastrado no CRM.")
        print("="*60)
        return

    print("📢 [ABORDAGENS GERADAS AUTOMATICAMENTE PELA IA (CSO)]:\n")
    resumo_para_cmo = ""
    
    for c in clientes:
        print(f"👤 Cliente: {c['nome']} | Compra: {c['produto']}")
        
        # O Gemini gera a cópia de vendas personalizada com base no histórico real
        script_ia = gerar_script_vendas_whatsapp(
            nome_cliente=c['nome'],
            produto=c['produto'],
            motivo="Pós-venda e retenção com frete grátis em Itabuna"
        )
        print(f"💬 WhatsApp IA: {script_ia}")
        print("-" * 50)
        
        resumo_para_cmo += f"Cliente {c['nome']} comprou {c['produto']}. "

    print("\n💡 [ESTRATÉGIA DE MARKETING DINÂMICA DISSINADA PELA IA (CMO)]:")
    insight_ia = gerar_insights_cmo(f"Clientes mapeados: {resumo_para_cmo}")
    print(f"{insight_ia}")
    print("="*60)

if __name__ == "__main__":
    executar_radar_vendas_e_crm()