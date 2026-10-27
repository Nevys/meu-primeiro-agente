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
# ROTINAS DE ALERTAS PROATIVOS
# =====================================================================

async def checar_alertas_proativos(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    if not chat_id:
        return

    if hasattr(agente_coo, 'verificar_estoque_robusto'):
        res_estoque = agente_coo.verificar_estoque_robusto()
        if any(k in str(res_estoque).lower() for k in ["alerta", "crítico", "zerado", "baixo", "repor"]):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 **[ALERTA PROATIVO DE ESTOQUE]**\n\nVerificação periódica identificou atenções no inventário:\n\n{res_estoque}",
                parse_mode="Markdown"
            )

    if hasattr(agente_cfo, 'analisar_caixa'):
        res_caixa = agente_cfo.analisar_caixa()
        if any(k in str(res_caixa).lower() for k in ["atencao", "alerta", "negativo", "limite"]):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ **[ALERTA FINANCEIRO PROATIVO]**\n\nNotificação periódica da sua diretoria de finanças:\n\n{res_caixa}",
                parse_mode="Markdown"
            )

# =====================================================================
# HANDLERS DO TELEGRAM
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if context.job_queue:
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
        "🔒 **Segurança Ativa:** Lançamentos de caixa exigem confirmação por botão.\n"
        "🔔 **Alertas Proativos Ativados:** Monitoramento ativo a cada 4h."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def status_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id)) if context.job_queue else []
    
    if jobs:
        proxima_exec = jobs[0].next_t.strftime("%H:%M:%S") if jobs[0].next_t else "Em breve"
        await update.message.reply_text(
            f"🟢 **Sistema Proativo Operacional!**\n\n"
            f"• **Monitoramento de Estoque/Caixa:** Ativo\n"
            f"• **Frequência:** A cada 4 horas\n"
            f"• **Próxima verificação agendada:** {proxima_exec}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Atenção:** Os alertas proativos não estão agendados.\n\nEnvie o comando `/start` para ativar.",
            parse_mode="Markdown"
        )


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

    # 1. INTERCEPTAÇÃO FORÇADA DE VENDAS / LANÇAMENTOS (ANTES DA IA DIRETORIA)
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "recebi", "entrada", "caixa", "faturou", "ganhei"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(char.isdigit() for char in mensagem_texto):
        prompt_parser = f'Extraia estritamente o valor financeiro numérico total (ex: se "vendi 50" e o contexto for 50 reais ou quantidade multiplicada, extraia o valor em R$ ou número) e uma descrição curta. Responda APENAS em JSON puro, sem crases, sem markdown: {{"valor": 50.0, "descricao": "venda no bar"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            # Limpeza rigorosa de blocos de código caso a IA insira crases
            json_limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(json_limpo[json_limpo.find("{"):json_limpo.rfind("}")+1])
            valor = float(dados.get("valor", 0))
            descricao = str(dados.get("descricao", mensagem_texto))

            if valor > 0:
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

    # 2. INTERCEPTAÇÃO DE CADASTRO DE CLIENTE CRM
    gatilhos_crm = ["cadastra cliente", "cadastrar cliente", "novo cliente", "salvar cliente", "adicionar cliente"]
    if any(k in msg_lower for k in gatilhos_crm):
        prompt_crm = f'Extraia nome e telefone. Responda APENAS em JSON puro, sem crases, sem markdown: {{"nome": "Nome", "telefone": "73900000000"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_crm)
        try:
            json_limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(json_limpo[json_limpo.find("{"):json_limpo.rfind("}")+1])
            nome = str(dados.get("nome", "Cliente"))
            telefone = str(dados.get("telefone", ""))

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

    # 3. CONSULTAS GERAIS AOS AGENTES (Caso não seja uma intenção de escrita)
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
        sucesso = lancar_no_caixa(dado_pendente["valor"], dado_pendente["descricao"], tipo="Entrada")
        if sucesso:
            await query.edit_message_text(
                f"✅ **Lançamento Registrado no Airtable!**\n\n"
                f"💰 **Valor:** R$ {dado_pendente['valor']:.2f}\n"
                f"📝 **Descrição:** {dado_pendente['descricao']}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Falha ao gravar lançamento no Airtable.")
        pendencias_confirmacao.pop(chat_id, None)

    elif query.data == "conf_caixa_nao":
        await query.edit_message_text("🚫 **Lançamento cancelado pelo usuário.**")
        pendencias_confirmacao.pop(chat_id, None)

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
    print("🤖 [BOT INTERATIVO ERP V3.3] Servidor Iniciado com Interceptação Rígida!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_comando))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_mensagem))
    app.add_handler(MessageHandler(filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(tratar_botoes_confirmacao))
    
    app.run_polling()