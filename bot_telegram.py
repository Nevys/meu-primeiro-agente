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
    return "☀️ Bot ERP Raio do Sol ativo com Travas e Interação por Botões!"

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

# Memória temporária para aguardar confirmação de lançamento (chat_id -> dados)
pendencias_confirmacao = {}

# =====================================================================
# FUNÇÕES DE INTEGRAÇÃO COM AIRTABLE
# =====================================================================

def lancar_no_caixa(valor, descricao, tipo="Entrada", unidade="Bar Raio do Sol"):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "records": [
            {
                "fields": {
                    "Descrição": descricao,
                    "Valor": float(valor),
                    "Tipo": tipo,
                    "Unidade": unidade
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

def popular_dados_ficticios_airtable():
    """Insere registros de teste no Airtable para validar os relatórios e DREs."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Caixa"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    registros_teste = [
        {"fields": {"Descrição": "Venda de Drinks (Teste)", "Valor": 350.0, "Tipo": "Entrada", "Unidade": "Bar Raio do Sol"}},
        {"fields": {"Descrição": "Compra de Insumos Bar (Teste)", "Valor": 120.0, "Tipo": "Saída", "Unidade": "Bar Raio do Sol"}},
        {"fields": {"Descrição": "Kit Eudora Completo (Teste)", "Valor": 280.0, "Tipo": "Entrada", "Unidade": "Fillara Cosméticos"}},
        {"fields": {"Descrição": "Reposição Estoque Perfumes (Teste)", "Valor": 150.0, "Tipo": "Saída", "Unidade": "Fillara Cosméticos"}},
        {"fields": {"Descrição": "Venda Linha Black (Teste)", "Valor": 200.0, "Tipo": "Entrada", "Unidade": "Linha Erótica"}}
    ]
    
    payload = {"records": registros_teste}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            return "✅ Dados fictícios de teste inseridos com sucesso no Airtable!"
        else:
            return f"⚠️ Erro ao inserir dados fictícios: {res.text}"
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
        "🔒 **Modo Seguro Ativo:** Todos os lançamentos exigem confirmação por botões e permitem observações.\n\n"
        "🛠️ **Comandos úteis:**\n"
        "• Envie qualquer venda (ex: *'Vendi 100 reais no bar com obs: mesa 4'*)\n"
        "• Digite `/popular` para gerar dados fictícios de teste no Airtable\n"
        "• Digite `/status` para checar o sistema"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def popular_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resultado = popular_dados_ficticios_airtable()
    await update.message.reply_text(resultado)

async def status_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **Sistema ERP Operacional com Travas de Confirmação ativas!**", parse_mode="Markdown")


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

    # 2. INTERCEPTAÇÃO RÍGIDA DE VENDAS E LANÇAMENTOS COM TRAVA E OBSERVAÇÃO
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "recebi", "entrada", "caixa", "faturou", "ganhei"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(char.isdigit() for char in mensagem_texto):
        prompt_parser = f'Extraia estritamente: 1. valor numérico, 2. descrição curta, 3. unidade ("Bar Raio do Sol", "Fillara Cosméticos" ou "Linha Erótica"), 4. observação extra se houver mencionada (ex: obs: ...). Responda APENAS em JSON puro, sem crases, sem markdown: {{"valor": 100.0, "descricao": "venda", "unidade": "Bar Raio do Sol", "observacao": "nenhuma"}}\nMensagem: {mensagem_texto}'
        json_resp = consultar_groq(prompt_parser)
        try:
            json_limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(json_limpo[json_limpo.find("{"):json_limpo.rfind("}")+1])
            valor = float(dados.get("valor", 0))
            descricao_base = str(dados.get("descricao", "Venda"))
            unidade = str(dados.get("unidade", "Bar Raio do Sol"))
            observacao = str(dados.get("observacao", ""))

            # Concatena a observação na descrição se o usuário enviou
            descricao_final = f"{descricao_base} | Obs: {observacao}" if observacao and observacao.lower() != "nenhuma" else descricao_base

            if valor > 0:
                pendencias_confirmacao[chat_id] = {
                    "tipo_acao": "caixa",
                    "valor": valor,
                    "descricao": descricao_final,
                    "unidade": unidade
                }

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirmar Lançamento", callback_data="conf_caixa_sim"),
                        InlineKeyboardButton("❌ Cancelar", callback_data="conf_caixa_nao")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"❓ **Deseja confirmar este lançamento no ERP?**\n\n"
                    f"🏢 **Negócio:** {unidade}\n"
                    f"💰 **Valor:** R$ {valor:.2f}\n"
                    f"📝 **Descrição / Obs:** {descricao_final}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
        except Exception as e:
            print(f"Erro no parser de caixa com obs: {e}")

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
        sucesso = lancar_no_caixa(dado_pendente["valor"], dado_pendente["descricao"], tipo="Entrada", unidade=dado_pendente["unidade"])
        if sucesso:
            await query.edit_message_text(
                f"✅ **Lançamento Gravado com Sucesso no Airtable!**\n\n"
                f"🏢 **Negócio:** {dado_pendente['unidade']}\n"
                f"💰 **Valor:** R$ {dado_pendente['valor']:.2f}\n"
                f"📝 **Detalhes:** {dado_pendente['descricao']}",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Falha ao gravar no Airtable. Verifique sua conexão.")
        pendencias_confirmacao.pop(chat_id, None)

    elif query.data == "conf_caixa_nao":
        await query.edit_message_text("🚫 **Lançamento cancelado com segurança.** Nenhum dado foi salvo.")
        pendencias_confirmacao.pop(chat_id, None)


if __name__ == "__main__":
    print("🤖 [BOT INTERATIVO ERP V4.0] Com Travas, Botões e Observações Ativo!")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("popular", popular_comando))
    app.add_handler(CommandHandler("status", status_comando))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_mensagem))
    app.add_handler(MessageHandler(filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(tratar_botoes_confirmacao))
    
    app.run_polling()