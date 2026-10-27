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

# --- SERVIDOR FLASK PARA MANTER O WEB SERVICE DO RENDER ATIVO ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "☀️ Bot ERP Raio do Sol rodando no Render!"

def rodar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# Inicia o servidor em segundo plano para liberar o bot do Telegram
threading.Thread(target=rodar_servidor_web, daemon=True).start()

# --- CONFIGURAÇÕES DE API ---
TELEGRAM_TOKEN = "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8".strip()
GROQ_API_KEY = "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".strip()
AIRTABLE_TOKEN = "pat4s5Nn72mN7S1B2.1f9b3310fdfd00c3b9ec8be9bb503fef404be1d01168fefb70296ba181c02bf9"
AIRTABLE_BASE_ID = "appjM48jtF1tccYVq"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

AIRTABLE_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# --- FUNÇÕES DE ESCRITA NO AIRTABLE ---
def lancar_no_caixa(valor, descricao, tipo="Entrada"):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    payload = {"records": [{"fields": {"Descrição": descricao, "Valor": float(valor), "Tipo": tipo}}]}
    res = requests.post(url, headers=AIRTABLE_HEADERS, json=payload, timeout=10)
    return res.status_code in [200, 201]

def cadastrar_cliente_crm(nome, telefone, historico=""):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/CRM"
    payload = {"records": [{"fields": {"Nome": nome, "Telefone": telefone, "Histórico de Compras": historico}}]}
    res = requests.post(url, headers=AIRTABLE_HEADERS, json=payload, timeout=10)
    return res.status_code in [200, 201]

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

# --- PROCESSAMENTO DO BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "☀️ **Diretoria Virtual - Bar Raio do Sol, Fillara & Linha Erótica**\n\n"
        "Envie mensagens por **texto** ou **áudio** para consultar ou registrar informações."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem_texto = ""
    if update.message.voice:
        await update.message.reply_text("🎙️ *Ouvindo seu áudio...*", parse_mode="Markdown")
        file = await context.bot.get_file(update.message.voice.file_id)
        caminho_audio = "temp_voz.ogg"
        await file.download_to_drive(caminho_audio)
        mensagem_texto = transcrever_audio_groq(caminho_audio)
        if os.path.exists(caminho_audio):
            os.remove(caminho_audio)
        if not mensagem_texto:
            await update.message.reply_text("❌ Não consegui processar o áudio.")
            return
        await update.message.reply_text(f"📝 *Transcrição:* \"{mensagem_texto}\"", parse_mode="Markdown")
    else:
        mensagem_texto = update.message.text

    msg_lower = mensagem_texto.lower()

    if any(k in msg_lower for k in ["registra entrada", "lança entrada", "registra venda", "lançar venda"]):
        prompt_parser = f'Extraia o valor numérico e a descrição. Responda em JSON: {{"valor": 100.0, "descricao": "venda"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            dados = json.loads(json_resp[json_resp.find("{"):json_resp.rfind("}")+1])
            if lancar_no_caixa(dados.get("valor", 0), dados.get("descricao", "Venda via Telegram"), tipo="Entrada"):
                await update.message.reply_text(f"✅ **Lançamento Registrado no Caixa!**\n💰 R$ {dados.get('valor'):.2f} - {dados.get('descricao')}")
                return
        except Exception:
            pass

    if any(k in msg_lower for k in ["cadastra cliente", "cadastrar cliente"]):
        prompt_crm = f'Extraia nome e telefone. Responda em JSON: {{"nome": "Nome", "telefone": "7300000000"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_crm)
        try:
            dados = json.loads(json_resp[json_resp.find("{"):json_resp.rfind("}")+1])
            if cadastrar_cliente_crm(dados.get("nome"), dados.get("telefone", "")):
                await update.message.reply_text(f"👤 **Cliente Cadastrado no CRM!**\n{dados.get('nome')} - {dados.get('telefone')}")
                return
        except Exception:
            pass

    contexto_erp = ""
    if any(k in msg_lower for k in ["estoque", "falta", "coo", "inventario"]):
        if hasattr(agente_coo, 'verificar_estoque_robusto'):
            contexto_erp = f"Dados COO: {agente_coo.verificar_estoque_robusto()}"
    elif any(k in msg_lower for k in ["caixa", "saldo", "mei", "cfo"]):
        if hasattr(agente_cfo, 'analisar_caixa'):
            contexto_erp = f"Dados CFO: {agente_cfo.analisar_caixa()}"

    prompt_sistema = "Você é o Diretor Executivo dos negócios Bar Raio do Sol, Fillara Cosméticos e Linha Erótica em Itabuna/BA."
    resposta_ia = consultar_groq(prompt_sistema, contexto_dados=f"Solicitação: {mensagem_texto}\n{contexto_erp}")
    await update.message.reply_text(resposta_ia)

if __name__ == "__main__":
    print("🤖 [BOT TELEGRAM + FLASK] Servidor iniciado!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_mensagem))
    app.add_handler(MessageHandler(filters.VOICE, processar_mensagem))
    app.run_polling()