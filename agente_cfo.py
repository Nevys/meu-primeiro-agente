import requests

AIRTABLE_TOKEN = "patem3xqKRjc8qGRP.7a082d5cca20b0507331dfc90d63804bdd3607ab7f0d2849a37a38254ccb3465".strip()
BASE_ID = "appjM48jtF1tccYVq".strip()
TABELA_CAIXA = "Caixa"

def obter_resumo_caixa():
    """Lê a aba Caixa no Airtable e calcula o saldo acumulado."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABELA_CAIXA}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        resposta = requests.get(url, headers=headers)
        dados = resposta.json()
        
        if 'error' in dados:
            return {"sucesso": False, "erro": dados['error']}
            
        receita_total = 0.0
        custos_totais = 0.0
        taxas_totais = 0.0
        
        for reg in dados.get('records', []):
            campos = reg.get('fields', {})
            
            raw_rec = campos.get('Receita Bruta')
            raw_cust = campos.get('Custos')
            raw_taxa = campos.get('Taxas')
            
            try:
                receita_total += float(raw_rec) if raw_rec is not None else 0.0
                custos_totais += float(raw_cust) if raw_cust is not None else 0.0
                taxas_totais += float(raw_taxa) if raw_taxa is not None else 0.0
            except (ValueError, TypeError):
                continue
                
        lucro_liquido = receita_total - custos_totais - taxas_totais
        return {
            "sucesso": True,
            "receita_total": receita_total,
            "custos_totais": custos_totais,
            "taxas_totais": taxas_totais,
            "lucro_liquido": lucro_liquido
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def analisar_aprovacao_financeira(orcamento_necessario=198.00):
    print("="*60)
    print("👔 [CFO Virtual] Analisando liquidez de caixa e teto fiscal...\n")
    
    resumo = obter_resumo_caixa()
    if not resumo["sucesso"]:
        print(f"❌ Erro ao consultar a aba Caixa: {resumo['erro']}")
        return
        
    saldo = resumo["lucro_liquido"]
    receita = resumo["receita_total"]
    
    print(f"📊 RECEITA BRUTA ACUMULADA: R$ {receita:.2f}")
    print(f"💵 SALDO LÍQUIDO EM CAIXA: R$ {saldo:.2f}")
    print(f"🛍️ ORÇAMENTO SOLICITADO PELO CPO: R$ {orcamento_necessario:.2f}")
    print("-" * 50)
    
    # Validação de Margem / Caixa
    if saldo >= orcamento_necessario:
        sobra = saldo - orcamento_necessario
        print("✅ APROVADO: Há caixa suficiente para cobrir o pedido sem comprometer a operação.")
        print(f"💰 Saldo projetado após a compra: R$ {sobra:.2f}")
    else:
        deficit = orcamento_necessario - saldo
        print("🛑 RECUSADO / ALERTA DE FLUXO: Caixa insuficiente para aprovar a compra total.")
        print(f"⚠️ Faltam R$ {deficit:.2f} em caixa. Priorize o item de maior giro (Gelo) ou aguarde novas entradas.")
        
    print("-" * 50)
    # Alerta Teto MEI (R$ 81.000 / ano)
    LIMITE_MEI = 81000.00
    percentual_mei = (receita / LIMITE_MEI) * 100
    print(f"📈 Termômetro MEI: R$ {receita:.2f} / R$ {LIMITE_MEI:.2f} ({percentual_mei:.1f}% utilizado)")
    print("="*60)

if __name__ == "__main__":
    analisar_aprovacao_financeira()