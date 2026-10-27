import requests

GROQ_API_KEY = "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".strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Modelos confirmados e ativos diretamente na sua chave Groq
MODELOS_ATIVOS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b"
]

def consultar_groq(prompt_sistema, contexto_dados=""):
    """
    Consulta a API do Groq utilizando os modelos ativos confirmados na sua chave.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt_completo = prompt_sistema
    if contexto_dados:
        prompt_completo += f"\n\n[DADOS DO ERP / CONTEXTO]:\n{contexto_dados}"

    for modelo in MODELOS_ATIVOS:
        payload = {
            "model": modelo,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é o Diretor Virtual especialista em IA responsável pelo Bar Raio do Sol, "
                        "Fillara Cosméticos e Linha Erótica/Black em Itabuna, Bahia. "
                        "Gere respostas práticas, diretas, persuasivas e sem enrolação."
                    )
                },
                {"role": "user", "content": prompt_completo}
            ],
            "temperature": 0.7
        }

        try:
            resposta = requests.post(GROQ_URL, json=payload, headers=headers, timeout=15)
            dados = resposta.json()

            if resposta.status_code == 200 and "choices" in dados and len(dados["choices"]) > 0:
                return dados["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    return "⚠️ Falha ao obter resposta dos modelos do Groq."


# =====================================================================
# FUNÇÕES ESPECIALISTAS INTEGRADAS AO ERP
# =====================================================================

def gerar_script_vendas_whatsapp(nome_cliente, produto, motivo="pos_venda"):
    prompt = (
        "Escreva uma mensagem de WhatsApp muito curta, direta e persuasiva (máximo 2 frases). "
        "Use um tom natural e amigável focado no público de Itabuna/BA."
    )
    contexto = f"Cliente: {nome_cliente} | Produto: {produto} | Motivo: {motivo}"
    return consultar_groq(prompt, contexto)


def gerar_insights_cmo(relatorio_estoque_caixa):
    prompt = (
        "Com base no relatório do ERP, sugira 2 ações práticas e imediatas de marketing "
        "ou combos promocionais para alavancar as vendas hoje."
    )
    return consultar_groq(prompt, relatorio_estoque_caixa)


def analisar_expansao_mercado(produto, categoria):
    prompt = (
        "Escreva 1 dica curta de oferta e posicionamento discreto e persuasivo para vendas no WhatsApp."
    )
    contexto = f"Produto: {produto} | Categoria: {categoria} | Região: Itabuna/BA"
    return consultar_groq(prompt, contexto)


# =====================================================================
# BLOCO DE TESTE E VALIDAÇÃO
# =====================================================================
if __name__ == "__main__":
    print("="*60)
    print("⚡ [VALIDAÇÃO COM MODELOS CONFIRMADOS] Testando agente_ia.py...\n")

    print("💬 1. SCRIPT PERSONALIZADO DE VENDAS (CSO):")
    script = gerar_script_vendas_whatsapp(
        nome_cliente="Maria Silva", 
        produto="Perfume O.U.i", 
        motivo="Oferecer refil com frete grátis em Itabuna"
    )
    print(f"{script}\n")

    print("-" * 50)

    print("💡 2. INSIGHTS DE MARKETING (CMO):")
    insight = gerar_insights_cmo(
        "Estoque Bar: Combo Vodka baixo. Fillara: Perfume O.U.i reposto. Linha Erótica: Gel Sensual em alta."
    )
    print(f"{insight}\n")

    print("-" * 50)

    print("🔥 3. ANÁLISE DE MERCADO / NOVAS LINHAS:")
    analise = analisar_expansao_mercado("Gel Sensual Vibrável", "Produtos Eróticos")
    print(f"{analise}\n")

    print("="*60)