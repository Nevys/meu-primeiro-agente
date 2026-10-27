import os
import json
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import agente_coo
import agente_cpo
import agente_cfo
from agente_ia import consultar_groq

# --- SERVIDOR FLASK PARA MANTER O RENDER ATIVO ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "☀️ Bot ERP Raio do Sol ativo e conectado ao Airtable!"

def rodar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

threading.Thread(target=rodar_servidor_web, daemon=True).start()

# --- CONFIGURAÇÕES DE API COM O NOVO TOKEN EMBUTIDO ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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").strip()
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# =====================================================================
# FUNÇÕES DE INTEGRAÇÃO COM AIRTABLE
# =====================================================================

def lancar_no_caixa(valor, descricao, tipo="Entrada"):
    """Insere registro no Caixa do Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "records": [
            {
                "fields": {
                    "Descrição": descricao,
                    "Valor": float(valor),
                    "Tipo": tipo
                }
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao lançar no caixa: {e}")
        return False


def cadastrar_cliente_crm(nome, telefone, historico=""):
    """Insere novo cliente no CRM do Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/CRM"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "records": [
            {
                "fields": {
                    "Nome": nome,
                    "Telefone": telefone,
                    "Histórico de Compras": historico
                }
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao cadastrar no CRM: {e}")
        return False


def transcrever_audio_groq(caminho_arquivo_audio):
    """Transcreve áudio do Telegram (.ogg) usando Whisper no Groq Cloud."""
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
# ROTEAMENTO E PROCESSAMENTO DE COMANDOS
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "☀️ **Diretoria Virtual - Bar Raio do Sol, Fillara & Linha Erótica**\n\n"
        "Envie mensagens por **texto** ou **áudio** para consultar ou registrar informações no seu ERP.\n\n"
        "💡 **Exemplos:**\n"
        "• *'Qual a situação do meu estoque?'*\n"
        "• *'Registra entrada de 150 reais de vendas do bar'* \n"
        "• *'Cadastra cliente Marcos, telefone 73999998888'*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # 1. ESCRITA: Registro no Caixa
    if any(k in msg_lower for k in ["registra entrada", "lança entrada", "registra venda", "lançar venda", "registrar caixa", "lançar caixa"]):
        prompt_parser = f'Extraia o valor numérico e a descrição da mensagem. Responda ESTRITAMENTE em formato JSON: {{"valor": 100.0, "descricao": "venda de bebidas"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            dados = json.loads(json_resp[json_resp.find("{"):json_resp.rfind("}")+1])
            if lancar_no_caixa(dados.get("valor", 0), dados.get("descricao", "Venda via Telegram"), tipo="Entrada"):
                await update.message.reply_text(f"✅ **Lançamento