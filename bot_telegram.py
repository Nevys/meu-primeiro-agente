import os
import json
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

import agente_coo
import agente_cpo
import agente_cfo
from agente_ia import consultar_groq

# --- SERVIDOR FLASK PARA MANTER O RENDER ATIVO ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "☀️ Bot ERP Raio do Sol ativo com Estrutura Financeira Avançada do Airtable!"

def rodar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

threading.Thread(target=rodar_servidor_web, daemon=True).start()

# --- CONFIGURAÇÕES DE API ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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").strip()
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Memória temporária para aguardar confirmação de lançamento
pendencias_confirmacao = {}

# =====================================================================
# FUNÇÕES DE INTEGRAÇÃO COM AIRTABLE (AJUSTADAS À SUA TABELA)
# =====================================================================

def lancar_no_caixa_avancado(receita_bruta, custos, taxas, unidade, data_str):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "records": [
            {
                "fields": {
                    "Dados": data_str,
                    "Receita Bruta": float(receita_bruta),
                    "Custos": float(custos),
                    "Taxas": float(taxas),
                    "Unidade": unidade
                }
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Status Airtable Caixa: {res.status_code} - {res.text}")
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao lançar no caixa avançado: {e}")
        return False

def popular_dados_ficticios_airtable():
    """Insere registros de teste no Airtable compatíveis com sua nova tabela de Caixa."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    registros_teste = [
        {"fields": {"Dados": "2026-10-25", "Receita Bruta": 1500.0, "Custos": 600.0, "Taxas": 50.0, "Unidade": "Bar Raio do Sol"}},
        {"fields": {"Dados": "2026-10-25", "Receita Bruta": 900.0, "Custos": 300.0, "Taxas": 40.0, "Unidade": "Fillara Cosméticos"}},
        {"fields": {"Dados": "2026-10-25", "Receita Bruta": 600.0, "Custos": 200.0, "Taxas": 20.0, "Unidade": "Linha Erótica"}}
    ]
    
    payload = {"records": registros_teste}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            return "✅ Dados fictícios inseridos com sucesso na sua nova tabela de Caixa do Airtable!"
        else:
            return f"⚠️ Erro ao inserir dados ({res.status_code}): {res.text}"
    except Exception as e:
        return f"❌ Erro de conexão ao popular Airtable: {e}"

def transcrever_audio_groq(caminho_arquivo_audio):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        with open(caminho_arquivo_audio, "rb") as audio_file:
            files = {
                "file": (caminho_arquivo_audio, audio_file, "audio/ogg"),
                "model": (None, "whisper-large-v3-turbo"),
                "language": (None, "pt")
            }
            res = requests.post(GROQ_AUDIO_URL, headers=headers, files=files, timeout=20)
            if res.status_code == 200:
                return res.json().get("text", "")
    except Exception as e:
        print(f"Erro na transcrição de áudio: {e}")
    return None

# =====================================================================
# HANDLERS DO TELEGRAM
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "☀️ **Diretoria Virtual - Bar Raio do Sol, Fillara & Linha Erótica**\n\n"
        "📊 **Estrutura de Caixa Avançada Vinculada ao Airtable!**\n"
        "• Envie vendas informando Receita, Custos e Taxas (ex: *'Vendi 1200 com custo 400 e taxa 50 na Fillara'*)\n"
        "• Digite `/popular` para injetar dados de teste na sua nova tabela\n"
        "• Digite `/status` para checar o bot"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def popular_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resultado = popular_dados_ficticios_airtable()
    await update.message.reply_text(resultado)

async def status_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **Sistema ERP Operacional integrado ao novo formato de Caixa do Airtable!**", parse_mode="Markdown")


async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mensagem_texto = ""

    if update.message.voice:
        await update.message.reply_text("🎙️ *Ouvindo e processando seu áudio...*", parse_mode="Markdown")
        file = await context.bot.get_file(update.message.voice.file_id)
        caminho_audio = "temp_voz.ogg"
        await file.download_to_drive(caminho_audio)
        
        mensagem_texto = transcrever_audio_groq(caminho_audio)
        if os.path.exists(caminho_audio):
            os.remove(caminho_audio)
            
        if not mensagem_texto:
            await update.message.reply_text("❌ Não consegui processar o áudio. Tente novamente.")
            return
            
        await update.message.reply_text(f"📝 *Transcrição:* \"{mensagem_texto}\"", parse_mode="Markdown")
    else:
        mensagem_texto = update.message.text

    msg_lower = mensagem_texto.lower()

    # 1. CONSULTA DE DRE POR UNIDADE
    if any(k in msg_lower for k in ["dre", "balanço", "relatório financeiro", "lucro"]):
        if "fillara" in msg_lower or "cosméticos" in msg_lower:
            resultado_dre = agente_cfo.gerar_dre_unidade("Fillara Cosméticos")
        elif "erótica" in msg_lower or "linha erótica" in msg_lower or "black" in msg_lower:
            resultado_dre = agente_cfo.gerar_dre_unidade("Linha Erótica")
        else:
            resultado_dre = agente_cfo.gerar_dre_unidade("Bar Raio do Sol")
            
        await update.message.reply_text(resultado_dre, parse_mode="Markdown")
        return

    # 2. INTERCEPTAÇÃO DE LANÇAMENTOS FINANCEIROS AVANÇADOS (Receita, Custos, Taxas)
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "recebi", "entrada", "caixa", "faturou", "ganhei"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(char.isdigit() for char in mensagem_texto):
        prompt_parser = f'Extraia estritamente em JSON puro sem crases: 1. receita_bruta (número), 2. custos (número, se não citado estime 30%), 3. taxas (número, se não citado estime 5%), 4. unidade ("Bar Raio do Sol", "Fillara Cosméticos" ou "Linha Erótica"), 5. data no formato AAAA-MM-DD (use a data atual 2026-10-26 se não informada). Exemplo: {{"receita_bruta": 1200.0, "custos": 450.0, "taxas": 60.0, "unidade": "Bar Raio do Sol", "data": "2026-10-26"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            json_limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(json_limpo[json_limpo.find("{"):json_limpo.rfind("}")+1])
            
            receita = float(dados.get("receita_bruta", 0))
            custos = float(dados.get("custos", 0))
            taxas = float(dados.get("taxas", 0))
            unidade = str(dados.get("unidade", "Bar Raio do Sol"))
            data_reg = str(dados.get("data", "2026-10-26"))

            if receita > 0:
                pendencias_confirmacao[chat_id] = {
                    "tipo_acao": "caixa_avancado",
                    "receita_bruta": receita,
                    "custos": custos,
                    "taxas": taxas,
                    "unidade": unidade,
                    "data": data_reg
                }

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirmar no Airtable", callback_data="conf_caixa_sim"),
                        InlineKeyboardButton("❌ Cancelar", callback_data="conf_caixa_nao")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                lucro_estimado = receita - custos - taxas
                await update.message.reply_text(
                    f"❓ **Deseja confirmar este lançamento financeiro?**\n\n"
                    f"🏢 **Negócio:** {unidade}\n"
                    f"📅 **Data:** {data_reg}\n"
                    f"💰 **Receita Bruta:** R$ {receita:.2f}\n"
                    f"💸 **Custos:** R$ {custos:.2f}\n"
                    f"🏷️ **Taxas:** R$ {taxas:.2f}\n"
                    f"📈 **Lucro Líquido Previsto:** R$ {lucro_estimado:.2f}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            print(f"Erro no parser financeiro avançado: {e}")

    # 3. CONSULTAS GERAIS AOS AGENTES
    contexto_erp = ""
    if any(k in msg_lower for k in ["estoque", "falta", "coo", "inventario", "reposicao"]):
        if hasattr(agente_coo, 'verificar_estoque_robusto'):
            contexto_erp = f"Dados do COO (Estoque Airtable): {agente_coo.verificar_estoque_robusto()}"
    elif any(k in msg_lower for k in ["caixa", "saldo", "mei", "cfo", "financeiro"]):
        if hasattr(agente_cfo, 'analisar_caixa'):
            contexto_erp = f"Dados do CFO (Caixa Airtable): {agente_cfo.analisar_caixa()}"

    prompt_sistema = (
        "Você é o Diretor Executivo dos negócios Bar Raio do Sol, Fillara Cosméticos e Linha Erótica em Itabuna/BA. "
        "Responda ao usuário com clareza, objetividade e foco em resultados operacionais."
    )
    resposta_ia = consultar_groq(prompt_sistema, contexto_dados=f"Solicitação do Usuário: {mensagem_texto}\n{contexto_erp}")
    await update.message.reply_text(resposta_ia)


# =====================================================================
# PROCESSAMENTO DOS BOTÕES DE CONFIRMAÇÃO
# =====================================================================

async def tratar_botoes_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    dado_pendente = pendencias_confirmacao.get(chat_id)

    if not dado_pendente:
        await query.edit_message_text("⚠️ Ação expirada ou já processada.")
        return

    if query.data == "conf_caixa_sim":
        sucesso = lancar_no_caixa_avancado(
            dado_pendente["receita_bruta"],
            dado_pendente["custos"],
            dado_pendente["taxas"],
            dado_pendente["unidade"],
            dado_pendente["data"]
        )
        if sucesso:
            await query.edit_message_text(
                f"✅ **Lançamento Financeiro Gravado no Airtable!**\n\n"
                f"🏢 **Negócio:** {dado_pendente['unidade']}\n"
                f"💰 **Receita:** R$ {dado_pendente['receita_bruta']:.2f}\n"
                f"💸 **Custos:** R$ {dado_pendente['custos']:.2f}\n"
                f"🏷️ **Taxas:** R$ {dado_pendente['taxas']:.2f}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Falha ao gravar na nova tabela do Airtable.")
        pendencias_confirmacao.pop(chat_id, None)

    elif query.data == "conf_caixa_nao":
        await query.edit_message_text("🚫 **Lançamento cancelado com segurança.**")
        pendencias_confirmacao.pop(chat_id, None)


if __name__ == "__main__":
    print("🤖 [BOT INTERATIVO ERP V4.1] Compatível com Tabela Avançada do Airtable!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("popular", popular_comando))
    app.add_handler(CommandHandler("status", status_comando))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_mensagem))
    app.add_handler(MessageHandler(filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(tratar_botoes_confirmacao))
    
    app.run_polling()