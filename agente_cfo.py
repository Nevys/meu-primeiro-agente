import os
from google import genai
from google.genai import types

# 1. INSIRA SUA CHAVE DA API AQUI
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6Ia7knuOUhdwdnr3TMg8i3gpi60VY2W9EQslvDRe1p9Og"
client = genai.Client()

# 2. A FERRAMENTA DO CFO (A ponte entre a IA e seus números)
def registrar_fechamento_caixa(receita_bruta: float, custo_produtos: float, taxas: float) -> str:
    """
    Registra o fechamento do dia no banco de dados e calcula as margens reais.
    Deve ser chamada sempre que o usuário informar os números de vendas e custos.
    """
    lucro_liquido = receita_bruta - custo_produtos - taxas
    margem = (lucro_liquido / receita_bruta) * 100 if receita_bruta > 0 else 0
    
    # [FUTURO]: Aqui colocaremos o código que envia esses dados direto para o seu Airtable/AppSheet
    
    resposta_sistema = (
        f"DADOS SALVOS COM SUCESSO NO BANCO DE DADOS.\n"
        f"Lucro Líquido Calculado: R$ {lucro_liquido:.2f}\n"
        f"Margem de Lucro Real: {margem:.2f}%"
    )
    return resposta_sistema

# 3. O CÉREBRO DO CFO (O Prompt Executivo)
cfo_prompt = """
Você é o CFO Virtual e Analista de Business Intelligence do Bar Raio do Sol e da Fillara Cosméticos.
Sua missão é blindar o caixa, otimizar margens de lucro e proteger o enquadramento fiscal do MEI.

REGRAS:
1. ZERO ALUCINAÇÃO: Nunca invente números. Use APENAS os dados fornecidos pelo usuário e os resultados das suas ferramentas.
2. SEMPRE ACIONE A FERRAMENTA: Se o usuário enviar dados de caixa, acione a ferramenta 'registrar_fechamento_caixa' antes de responder.
3. ANÁLISE PRAGMÁTICA: Calcule a Margem de Contribuição e o Lucro Líquido. Diga se a operação rodou no azul ou no vermelho.
4. CUSTOS OCULTOS: Avise se as taxas da plataforma ou maquininha estão corroendo o lucro.
5. FORMATAÇÃO EXECUTIVA: Apresente valores em BRL (R$ 1.500,00). Use tabelas Markdown. Seja frio, analítico e termine com um plano de ação de 1 passo.
"""

config = types.GenerateContentConfig(
    tools=[registrar_fechamento_caixa], # Entregando a ferramenta para a IA
    system_instruction=cfo_prompt,
    temperature=0.1, # Temperatura super baixa (0.1) para que ele seja frio, matemático e não invente coisas
)

# 4. O MOTOR DE EXECUÇÃO
def relatorio_diario_cfo(mensagem_usuario: str):
    print("="*50)
    print(f"🟢 VOCÊ: {mensagem_usuario}\n")
    
    # Enviando a mensagem para o CFO
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=mensagem_usuario,
        config=config
    )
    
    # Verificando se o CFO decidiu usar a calculadora/banco de dados
    if response.function_calls:
        for call in response.function_calls:
            print(f"[⚙️ O CFO acionou o sistema: {call.name}]")
            
            # Executando a matemática e salvando os dados
            resultado_ferramenta = registrar_fechamento_caixa(**call.args)
            print(f"[💾 Resposta do Sistema: {resultado_ferramenta}]\n")
            
            # CFO lê o resultado e escreve o relatório final
            resposta_final = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"O usuário disse: '{mensagem_usuario}'. O sistema de banco de dados retornou: '{resultado_ferramenta}'. Escreva o seu relatório executivo de CFO para o usuário.",
                config=types.GenerateContentConfig(system_instruction=cfo_prompt, temperature=0.1)
            )
            print(f"👔 CFO VIRTUAL:\n{resposta_final.text}")
    else:
        # Caso ele não precise calcular nada (ex: tirar uma dúvida)
        print(f"👔 CFO VIRTUAL:\n{response.text}")
    print("="*50)

# 5. O SEU TESTE REAL (Simulando o fim de um turno no Bar Raio do Sol)
if __name__ == "__main__":
    cenario_teste = (
        "Acabei de fechar o bar. Tivemos R$ 1.200 em vendas brutas de combos de bebida. "
        "O custo das garrafas e gelo foi de R$ 450. A maquininha de cartão nos cobrou R$ 60 de taxa. "
        "Analise esses números para mim."
    )
    relatorio_diario_cfo(cenario_teste)
