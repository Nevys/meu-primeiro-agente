import agente_cfo
import agente_coo

def processar_comando_orquestrado(intencao, dados):
    print(f"🧠 [ORQUESTRADOR] Roteando intenção: '{intencao}'")

    if intencao == "lancar_caixa_avancado":
        return agente_cfo.lancar_caixa_avancado(dados)
    
    elif intencao == "consultar_dre":
        unidade = dados.get("unidade", "Bar Raio do Sol")
        return agente_cfo.gerar_dre_unidade(unidade)

    elif intencao == "consultar_estoque":
        res = agente_coo.verificar_estoque_robusto()
        return str(res)
        
    elif intencao == "contagem_fisica":
        # Despacha a lista de itens parseada para o COO gravar
        return agente_coo.sincronizar_contagem_fisica(dados.get("itens", []))

    elif intencao == "popular_dados":
        teste = {"data": "2026-10-26", "receita_bruta": 1500.0, "custos": 500.0, "taxas": 50.0, "unidade": "Fillara Cosméticos"}
        return agente_cfo.lancar_caixa_avancado(teste)

    else:
        return "⚠️ Orquestrador: Intenção não reconhecida."