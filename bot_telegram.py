import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import orquestrador
from agente_ia import consultar_groq

web_app = Flask(__name__)

@web_app.route('/')
def home(): return "☀️ Bot ERP Raio do Sol Operacional!"

def rodar_servidor_web(): web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=rodar_servidor_web, daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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").strip()

pendencias_confirmacao = {}

def obter_menu_principal():
    keyboard = [
        [InlineKeyboardButton("📊 Consultar DRE / Saldo", callback_data="menu_dre")],
        [InlineKeyboardButton("💰 Como Lançar uma Venda", callback_data="menu_venda_instrucao")],
        [InlineKeyboardButton("📦 Auditado de Estoque (COO)", callback_data="menu_estoque")],
        [InlineKeyboardButton("🧪 Injetar Dados de Teste", callback_data="menu_popular")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "☀️ **Painel Executivo ERP - Diretoria Virtual**\n"
        "Bar Raio do Sol | Fillara Cosméticos | Linha Erótica\n\n"
        "Selecione uma opção abaixo para navegar:"
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=obter_menu_principal(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=obter_menu_principal(), parse_mode="Markdown")

async def popular_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resultado = orquestrador.processar_comando_orquestrado("popular_dados", {})
    await update.message.reply_text(f"🧪 **Teste de Injeção:**\n{resultado.get('mensagem', 'Feito')}")

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg_texto = update.message.text
    if not msg_texto: return
    msg_lower = msg_texto.lower()

    # 1. INTERCEPTAÇÃO DE CONTAGEM DE ESTOQUE (Textos com hífen e locais)
    gatilhos_estoque = ["prateleira", "pratileira", "geladeira", "freezer", "palete"]
    if any(k in msg_lower for k in gatilhos_estoque) and "-" in msg_texto:
        prompt = f'Extraia os itens e retorne APENAS um JSON puro no formato: [{{"produto": "nome", "quantidade": numero, "local": "Prateleira/Geladeira/Freezer/Palete"}}]. Mensagem: {msg_texto}'
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            lista_itens = json.loads(limpo[limpo.find("["):limpo.rfind("]")+1])
            
            if len(lista_itens) > 0:
                pendencias_confirmacao[chat_id] = {"intencao": "contagem_fisica", "itens": lista_itens}
                botoes = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"✅ Sincronizar {len(lista_itens)} Itens no Airtable", callback_data="conf_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_nao")
                ]])
                
                await update.message.reply_text(
                    f"📦 **Contagem de Estoque Detectada!**\nIdentificados {len(lista_itens)} produtos.\n\nDeseja gravar no Airtable?",
                    reply_markup=botoes, parse_mode="Markdown"
                )
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ **Erro ao ler estoque:** `{e}`", parse_mode="Markdown")
            return

    # 2. INTERCEPTAÇÃO DE LANÇAMENTOS FINANCEIROS
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "entrada"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(c.isdigit() for c in msg_texto):
        prompt = f'Extraia APENAS em JSON puro: {{"receita_bruta": num, "custos": num, "taxas": num, "unidade": "Bar Raio do Sol" ou "Fillara Cosméticos" ou "Linha Erótica", "data": "2026-10-27"}}. Msg: {msg_texto}'
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(limpo[limpo.find("{"):json_limpo.rfind("}")+1] if "{" in limpo else limpo)
            receita = float(dados.get("receita_bruta", 0))
            if receita > 0:
                pendencias_confirmacao[chat_id] = {
                    "intencao": "lancar_caixa_avancado", 
                    "receita_bruta": receita, 
                    "custos": float(dados.get("custos", 0)), 
                    "taxas": float(dados.get("taxas", 0)), 
                    "unidade": str(dados.get("unidade", "Bar Raio do Sol")), 
                    "data": "2026-10-27"
                }
                botoes = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Confirmar Lançamento", callback_data="conf_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_nao")
                ]])
                await update.message.reply_text(
                    f"❓ **Confirma este lançamento?**\n\n🏢 **Unidade:** {dados.get('unidade')}\n💰 **Receita:** R$ {receita:.2f}\n💸 **Custos:** R$ {dados.get('custos', 0):.2f}", 
                    reply_markup=botoes, parse_mode="Markdown"
                )
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ **Erro no parser financeiro:** `{e}`", parse_mode="Markdown")
            return

    # 3. SE O USUÁRIO DIGITAR MENSAGEM FORA DO PADRÃO -> RETORNA O MENU (NÃO BATE PAPO)
    await update.message.reply_text(
        "💡 Para realizar uma operação, utilize o menu guiado abaixo ou envie um lançamento direto (ex: *'Vendi 100 com custo 30 no bar'*):",
        reply_markup=obter_menu_principal(),
        parse_mode="Markdown"
    )

async def botoes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    # Submenus do Botão
    if data == "menu_dre":
        botoes = InlineKeyboardMarkup([
            [InlineKeyboardButton("☀️ Bar Raio do Sol", callback_data="dre_bar")],
            [InlineKeyboardButton("💄 Fillara Cosméticos", callback_data="dre_fillara")],
            [InlineKeyboardButton("🔥 Linha Erótica", callback_data="dre_erotica")],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="menu_voltar")]
        ])
        await query.edit_message_text("📊 **Escolha a unidade para consultar o DRE:**", reply_markup=botoes, parse_mode="Markdown")
        return

    elif data.startswith("dre_"):
        unidade = "Bar Raio do Sol" if data == "dre_bar" else "Fillara Cosméticos" if data == "dre_fillara" else "Linha Erótica"
        res = orquestrador.processar_comando_orquestrado("consultar_dre", {"unidade": unidade})
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="menu_voltar")]])
        await query.edit_message_text(f"{res}", reply_markup=botoes, parse_mode="Markdown")
        return

    elif data == "menu_venda_instrucao":
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="menu_voltar")]])
        await query.edit_message_text(
            "📝 **Como lançar uma venda:**\n\nEnvie uma frase como:\n• *'Vendi 150 com custo 50 e taxa 10 no bar'*\n• *'Lança receita de 200 na Fillara'*\n\nO bot exibirá os botões de confirmação antes de gravar no Airtable.",
            reply_markup=botoes, parse_mode="Markdown"
        )
        return

    elif data == "menu_estoque":
        res = orquestrador.processar_comando_orquestrado("consultar_estoque", {})
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="menu_voltar")]])
        await query.edit_message_text(f"{res}", reply_markup=botoes, parse_mode="Markdown")
        return

    elif data == "menu_popular":
        res = orquestrador.processar_comando_orquestrado("popular_dados", {})
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="menu_voltar")]])
        await query.edit_message_text(f"🧪 **Injeção de Teste:**\n{res.get('mensagem')}", reply_markup=botoes, parse_mode="Markdown")
        return

    elif data == "menu_voltar":
        await start(update, context)
        return

    # Processamento de Confirmações Sim / Não
    dado = pendencias_confirmacao.get(chat_id)
    if not dado:
        await query.edit_message_text("⚠️ Operação expirada ou já processada.", reply_markup=obter_menu_principal())
        return

    if data == "conf_sim":
        res = orquestrador.processar_comando_orquestrado(dado["intencao"], dado)
        if isinstance(res, dict) and res.get("sucesso"):
            await query.edit_message_text(f"✅ **Operação Concluída com Sucesso!**\n{res.get('mensagem')}", reply_markup=obter_menu_principal())
        else:
            msg_e = res.get("mensagem") if isinstance(res, dict) else str(res)
            await query.edit_message_text(f"❌ **Falha:** {msg_e}", reply_markup=obter_menu_principal())
        pendencias_confirmacao.pop(chat_id, None)

    elif data == "conf_nao":
        await query.edit_message_text("🚫 **Operação cancelada.**", reply_markup=obter_menu_principal())
        pendencias_confirmacao.pop(chat_id, None)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("popular", popular_comando))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(botoes_handler))
    app.run_polling()