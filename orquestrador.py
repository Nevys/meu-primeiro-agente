<<<<<<< HEAD
import sys
from agente_coo import verificar_estoque_robusto
from agente_cpo import gerar_ordens_de_compra
from agente_cfo import analisar_aprovacao_financeira
from agente_cmo_cso import executar_radar_vendas_e_crm

def executar_diagnostico_geral_erp():
    print("="*70)
    print("🧠 [ORQUESTRADOR CENTRAL] Iniciando Varredura Completa do ERP")
    print("   Bar Raio do Sol & Fillara Cosméticos")
    print("="*70 + "\n")

    # 1. Módulo Operacional (COO)
    print(">>> 1. AUDITORIA DE ESTOQUE (COO)")
    res_coo = verificar_estoque_robusto()
    
    orcamento_solicitado = 0.0
    tem_itens_faltando = False

    if res_coo["sucesso"]:
        alertas = res_coo["alertas"]
        tem_itens_faltando = any(len(v) > 0 for v in alertas.values())
        if tem_itens_faltando:
            print("🚨 Ruptura detectada! Itens precisam de reposição.")
        else:
            print("✅ Estoque em níveis seguros.")
    else:
        print(f"❌ Erro ao consultar COO: {res_coo['erro']}")

    print("\n" + "-"*70 + "\n")

    # 2. Módulo de Suprimentos (CPO)
    print(">>> 2. COTAÇÃO E ORDENS DE COMPRA (CPO)")
    if tem_itens_faltando:
        # O CPO executa e calcula o orçamento necessário
        gerar_ordens_de_compra()
        # Definimos o valor fixo do orçamento das compras pendentes identificadas no ciclo
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
=======

>>>>>>> 40b399fe3f77ec0a2977981530aee651d0437f5e
