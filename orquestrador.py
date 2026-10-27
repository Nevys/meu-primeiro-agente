import os
import requests
from agente_coo import verificar_estoque_robusto
from agente_cpo import gerar_ordens_de_compra
from agente_cfo import analisar_aprovacao_financeira, gerar_dre_unidade
from agente_cmo_cso import executar_radar_vendas_e_crm

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

def processar_comando_orquestrado(intencao, dados):
    """
    Dispatcher central do ERP. O Telegram envia a intenção e os dados extraídos,
    e o Orquestrador delega para o agente especialista executar na base de dados.
    """
    print(f"🧠 [ORQUESTRADOR] Roteando intenção: '{intencao}'")

    if intencao == "lancar_caixa_avancado":
        # Delega para o Agente CFO / Módulo Financeiro gravar no Airtable
        return _executar_gravacao_caixa(dados)
    
    elif intencao == "consultar_dre":
        # Delega para o Agente CFO gerar o DRE da unidade
        unidade = dados.get("unidade", "Bar Raio do Sol")
        return gerar_dre_unidade(unidade)

    elif intencao == "consultar_estoque":
        # Delega para o Agente COO
        res = verificar_estoque_robusto()
        return str(res)

    else:
        return "⚠️ Orquestrador: Intenção não reconhecida pelos agentes especialistas."

def _executar_gravacao_caixa(dados):
    """Função interna controlada pelo ecossistema de agentes para escrita no Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    payload = {
        "records": [
            {
                "fields": {
                    "Dados": dados.get("data", "2026-10-26"),
                    "Receita Bruta": float(dados.get("receita_bruta", 0.0)),
                    "Custos": float(dados.get("custos", 0.0)),
                    "Taxas": float(dados.get("taxas", 0.0)),
                    "Unidade": dados.get("unidade", "Bar Raio do Sol")
                }
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            return {"sucesso": True, "mensagem": "Lançamento gravado com sucesso no Airtable via Agente CFO."}
        else:
            return {"sucesso": False, "mensagem": f"Erro Airtable: {res.text}"}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro de conexão no orquestrador: {e}"}

def executar_diagnostico_geral_erp():
    print("="*70)
    print("🧠 [ORQUESTRADOR CENTRAL] Iniciando Varredura Completa do ERP")
    print("   Bar Raio do Sol, Fillara Cosméticos & Linha Erótica")
    print("="*70 + "\n")

    # 1. Módulo Operacional (COO)
    print(">>> 1. AUDITORIA DE ESTOQUE (COO)")
    res_coo = verificar_estoque_robusto()
    tem_itens_faltando = False
    if isinstance(res_coo, dict) and res_coo.get("sucesso"):
        alertas = res_coo.get("alertas", {})
        tem_itens_faltando = any(len(v) > 0 for v in alertas.values())
        print("🚨 Ruptura detectada!" if tem_itens_faltando else "✅ Estoque em níveis seguros.")
    else:
        print(f"ℹ️ Status COO: {res_coo}")

    print("\n" + "-"*70 + "\n")

    # 2. Módulo de Suprimentos (CPO)
    print(">>> 2. COTAÇÃO E ORDENS DE COMPRA (CPO)")
    orcamento_solicitado = 0.0
    if tem_itens_faltando:
        gerar_ordens_de_compra()
        orcamento_solicitado = 198.00 
    else:
        print("✅ Nenhuma cotação necessária no momento.")

    print("\n" + "-"*70 + "\n")

    # 3. Módulo Financeiro (CFO)
    print(">>> 3. ANÁLISE DE LIQUIDEZ E FLUXO DE CAIXA (CFO)")
    analisar_aprovacao_financeira(orcamento_necessario=orcamento_solicitado)

    print("\n" + "-"*70 + "\n")

    # 4. Módulo de Clientes e Vendas (CMO / CSO)
    print(">>> 4. RADAR DE VENDAS E CRM (CMO/CSO)")
    executar_radar_vendas_e_crm()

    print("="*70)
    print("✅ DIAGNÓSTICO ERP CONCLUÍDO COM SUCESSO.")
    print("="*70)

if __name__ == "__main__":
    executar_diagnostico_geral_erp()