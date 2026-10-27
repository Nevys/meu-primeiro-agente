import os
import requests

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

def analisar_caixa():
    """Analisa o saldo geral do caixa no Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return "Não foi possível acessar a tabela de Caixa no Airtable."
        
        records = res.json().get("records", [])
        total = 0.0
        for r in records:
            fields = r.get("fields", {})
            val = float(fields.get("Valor", 0.0))
            tipo = str(fields.get("Tipo", "Entrada")).lower()
            if "saida" in tipo or "despesa" in tipo or "retirada" in tipo:
                total -= val
            else:
                total += val
        return f"Saldo atual consolidado no Caixa: R$ {total:.2f}."
    except Exception as e:
        return f"Erro ao analisar caixa: {e}"

def gerar_dre_unidade(nome_unidade):
    """Calcula receitas, despesas e lucro líquido de uma unidade específica no Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return f"Erro ao acessar o Airtable para gerar DRE de {nome_unidade} (Status: {res.status_code})."
        
        records = res.json().get("records", [])
        total_entradas = 0.0
        total_saidas = 0.0
        total_registros = 0
        
        for record in records:
            fields = record.get("fields", {})
            unidade_reg = str(fields.get("Unidade", "Bar Raio do Sol"))
            
            # Se o registro não tiver unidade preenchida ou corresponder à buscada
            if nome_unidade.lower() in unidade_reg.lower() or not unidade_reg:
                total_registros += 1
                try:
                    valor = float(fields.get("Valor", 0.0))
                except (ValueError, TypeError):
                    valor = 0.0
                    
                tipo = str(fields.get("Tipo", "Entrada")).lower()
                
                if any(k in tipo for k in ["saida", "despesa", "retirada", "gasto"]):
                    total_saidas += valor
                else:
                    total_entradas += valor
                    
        lucro_liquido = total_entradas - total_saidas
        
        relatorio = (
            f"📊 **DRE Parcial - {nome_unidade}**\n\n"
            f"📦 **Lançamentos Analisados:** {total_registros}\n"
            f"💰 **Receitas Totais:** R$ {total_entradas:.2f}\n"
            f"💸 **Despesas / Custos:** R$ {total_saidas:.2f}\n"
            f"📈 **Resultado Operacional (Lucro):** R$ {lucro_liquido:.2f}"
        )
        return relatorio
    except Exception as e:
        return f"Erro interno ao calcular DRE: {e}"