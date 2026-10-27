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
    return "☀️ Bot ERP Raio do Sol ativo com Confirmações e Alertas Proativos!"

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

# Memória temporária para aguardar confirmação do usuário (chat_id -> dados)
pendencias_confirmacao = {}

# =====================================================================
# FUNÇÕES DE INTEGRAÇÃO COM AIRTABLE
# =====================================================================

def lancar_no_caixa(valor, descricao, tipo="Entrada"):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    payload = {"records": [{"fields": {"Descrição": descricao, "Valor": float(valor), "Tipo": tipo}}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao lançar no caixa: {e}")
        return False

def cadastrar_cliente_crm(nome, telefone, historico=""):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/CRM"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    payload = {"records": [{"fields": {"Nome": nome, "Telefone": telefone, "Histórico de Compras": historico}}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao cadastrar no CRM: {e}")
        return False

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
# ROTINAS DE ALERTAS PROATIVOS (ALERTAS AUTOMÁTICOS)
# =====================================================================

async def checar_alertas_proativos(context: ContextTypes.DEFAULT_TYPE):
    """Verifica periodicamente o estoque e caixa para enviar alertas no Telegram."""
    chat_id = context.job.chat_id
    if not chat_id:
        return

    # 1. Alerta de Estoque Crítico
    if hasattr(agente_coo, 'verificar_estoque_robusto'):
        res_estoque = agente_coo.verificar_estoque_robusto()
        if "alerta" in str(res_estoque).lower() or "crítico" in str(res_estoque).lower() or "zerado" in str(res_estoque).lower():
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 **[ALERTA PROATIVO DE ESTOQUE]**\n\nIdentifiquei itens em nível crítico no seu inventário:\n{res_estoque}",
                parse_mode="Markdown"
            )

    # 2. Alerta Financeiro / Caixa
    if hasattr(agente_cfo, 'analisar_caixa'):
        res_caixa = agente_cfo.analisar_caixa()
        if "atencao" in str(res_caixa).lower() or "alerta" in str(res_caixa).lower():
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ **[ALERTA FINANCEIRO PROATIVO]**\n\nNotificação da sua diretoria de finanças:\n{res_caixa}",
                parse_mode="Markdown"
            )

# =====================================================================
# HANDLERS DO TELEGRAM
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Agenda a rotina de alertas proativos para rodar a cada 4 horas (14400 segundos)
    if context.job_queue:
        # Remove agendamentos antigos para evitar duplicidade
        jobs_existentes = context.job_queue.get_jobs_by_name(str(chat_id))
        for job in jobs_existentes:
            job.schedule_removal()
            
        context.job_queue.run_repeating(
            checar_alertas_proativos,
            interval=14400,
            first=10,
            chat_id=chat_id,
            name=str(chat_id)
        )

    msg = (
        "☀️ **Diretoria Virtual - Bar Raio do Sol, Fillara & Linha Erótica**\n\n"
        "Envie mensagens por **texto** ou **áudio** para consultar ou registrar informações.\n\n"
        "🔒 **Segurança Ativa:** Todos os lançamentos exigirão sua confirmação antes de gravar no Airtable.\n"
        "🔔 **Alertas Proativos Ativados:** Notificarei você automaticamente sobre qualquer anomalia no estoque ou caixa."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


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

    # 1. ESCRITA COM CONFIRMAÇÃO PRÉVIA: Registro no Caixa
    if any(k in msg_lower for k in ["registra entrada", "lança entrada", "registra venda", "lançar venda", "registrar caixa", "lançar caixa"]):
        prompt_parser = f'Extraia o valor numérico e a descrição da mensagem. Responda ESTRITAMENTE em formato JSON: {{"valor": 100.0, "descricao": "venda de bebidas"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            dados = json.loads(json_resp[json_resp.find("{"):json_resp.rfind("}")+1])
            valor = dados.get("valor", 0)
            descricao = dados.get("descricao", "Venda via Telegram")

            # Armazena na memória de pendências
            pendencias_confirmacao[chat_id] = {
                "tipo_acao": "caixa",
                "valor": valor,
                "descricao": descricao
            }

            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirmar Lançamento", callback_data="conf_caixa_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_caixa_nao")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"❓ **Deseja confirmar o seguinte lançamento no Caixa?**\n\n"
                f"💰 **Valor:** R$ {valor:.2f}\n"
                f"📝 **Descrição:** {descricao}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            print(f"Erro no parser de caixa: {e}")

    # 2. ESCRITA COM CONFIRMAÇÃO PRÉVIA: Cadastro no CRM
    if any(k in msg_lower for k in ["cadastra cliente", "cadastrar cliente", "novo cliente"]):
        prompt_crm = f'Extraia nome e telefone. Responda ESTRITAMENTE em formato JSON: {{"nome": "Nome do Cliente", "telefone": "73900000000"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_crm)
        try:
            dados = json.loads(json_resp[json_resp.find("{"):json_resp.rfind("}")+1])
            nome = dados.get("nome", "Cliente")
            telefone = dados.get("telefone", "")

            pendencias_confirmacao[chat_id] = {
                "tipo_acao": "crm",
                "nome": nome,
                "telefone": telefone
            }

            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirmar Cadastro", callback_data="conf_crm_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_crm_nao")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"❓ **Deseja confirmar o cadastro do novo cliente?**\n\n"
                f"👤 **Nome:** {nome}\n"
                f"📞 **Telefone:** {telefone}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            print(f"Erro no parser CRM: {e}")

    # 3. LEITURA: Consultas aos Agentes
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
# PROCESSAMENTO DOS BOTÕES DE CONFIRMAÇÃO (CALLBACK BOTÕES)
# =====================================================================

async def tratar_botoes_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    dado_pendente = pendencias_confirmacao.get(chat_id)

    if not dado_pendente:
        await query.edit_message_text("⚠️ Ação expirada ou já processada.")
        return

    # Processa confirmação do Caixa
    if query.data == "conf_caixa_sim":
        sucesso = lancar_no_caixa(dado_pendente["valor"], dado_pendente["descricao"], tipo="Entrada")
        if sucesso:
            await query.edit_message_text(
                f"✅ **Lançamento Registrado no Airtable!**\n\n"
                f"💰 **Valor:** R$ {dado_pendente['valor']:.2f}\n"
                f"📝 **Descrição:** {dado_pendente['descricao']}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Falha ao gravar lançamento no Airtable. Verifique o token de acesso.")
        pendencias_confirmacao.pop(chat_id, None)

    elif query.data == "conf_caixa_nao":
        await query.edit_message_text("🚫 **Lançamento cancelado pelo usuário.**")
        pendencias_confirmacao.pop(chat_id, None)

    # Processa confirmação do CRM
    elif query.data == "conf_crm_sim":
        sucesso = cadastrar_cliente_crm(dado_pendente["nome"], dado_pendente["telefone"])
        if sucesso:
            await query.edit_message_text(
                f"👤 **Cliente Cadastrado no CRM com Sucesso!**\n\n"
                f"**Nome:** {dado_pendente['nome']}\n"
                f"**Telefone:** {dado_pendente['telefone']}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Falha ao cadastrar cliente no Airtable.")
        pendencias_confirmacao.pop(chat_id, None)

    elif query.data == "conf_crm_nao":
        await query.edit_message_text("🚫 **Cadastro de cliente cancelado pelo usuário.**")
        pendencias_confirmacao.pop(chat_id, None)


if __name__ == "__main__":
    print("🤖 [BOT INTERATIVO ERP V3] Servidor com Confirmação e Alertas Proativos Iniciado!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_mensagem))
    app.add_handler(MessageHandler(filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(tratar_botoes_confirmacao))
    
    app.run_polling()