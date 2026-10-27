import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import orquestrador
import agente_usuarios
from agente_ia import consultar_groq

web_app = Flask(__name__)

@web_app.route('/')
def home(): return "☀️ Bot ERP Raio do Sol Operacional com Controle de Perfis!"

def rodar_servidor_web(): web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=rodar_servidor_web, daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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").strip()

pendencias_confirmacao = {}

def obter_menu_por_perfil(cargo):
    """Gera menus dinâmicos com base no cargo do usuário no Airtable."""
    if cargo == "Dono":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 DRE Completo por Unidade", callback_data="menu_dre")],
            [InlineKeyboardButton("📦 Auditado de Estoque (COO)", callback_data="menu_estoque")],
            [InlineKeyboardButton("💵 Lançar Venda / Caixa", callback_data="menu_venda_instrucao")],
            [InlineKeyboardButton("🧪 Injetar Dados de Teste", callback_data="menu_popular")]
        ])
    elif cargo == "Funcionario":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Lançar Contagem de Estoque", callback_data="menu_contagem_instrucao")],
            [InlineKeyboardButton("💵 Registrar Venda do Turno", callback_data="menu_venda_instrucao")]
        ])
    else:  # Cliente
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💄 Catálogo Fillara Cosméticos", callback_data="cliente_fillara")],
            [InlineKeyboardButton("☀️ Cardápio Bar Raio do Sol", callback_data="cliente_bar")],
            [InlineKeyboardButton("🔥 Linha Erótica", callback_data="cliente_erotica")],
            [InlineKeyboardButton("💬 Falar com Atendente", callback_data="cliente_atendente")]
        ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Valida ou cadastra automaticamente
    dados_user = agente_usuarios.obter_ou_cadastrar_usuario(user.id, user.first_name)
    cargo = dados_user.get("cargo", "Cliente")

    msg = (
        f"☀️ **Bem-vindo(a), {user.first_name}!**\n"
        f"👤 **Perfil:** `{cargo}`\n\n"
        f"Selecione uma opção no menu abaixo:"
    )
    
    menu = obter_menu_por_perfil(cargo)
    if update.message:
        await update.message.reply_text(msg, reply_markup=menu, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=menu, parse_mode="Markdown")

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    msg_texto = update.message.text
    if not msg_texto: return
    
    dados_user = agente_usuarios.obter_ou_cadastrar_usuario(user.id, user.first_name)
    cargo = dados_user.get("cargo", "Cliente")

    # Restrição de segurança: Clientes não acionam comandos de caixa/estoque
    if cargo == "Cliente":
        res_ia = consultar_groq(
            "Você é a atendente virtual do Bar Raio do Sol, Fillara Cosméticos e Linha Erótica. "
            "Seja simpática, apresente os produtos e ajude o cliente com dúvidas de compras.", 
            f"Mensagem do cliente {user.first_name}: {msg_texto}"
        )
        await update.message.reply_text(res_ia)
        return

    # Ações para Funcionário e Dono
    msg_lower = msg_texto.lower()

    # INTERCEPTAÇÃO DE ESTOQUE
    gatilhos_estoque = ["prateleira", "pratileira", "geladeira", "freezer", "palete"]
    if any(k in msg_lower for k in gatilhos_estoque) and "-" in msg_texto:
        prompt = f'Extraia os itens e retorne APENAS JSON puro: [{{"produto": "nome", "quantidade": num, "local": "Prateleira/Geladeira/Freezer/Palete"}}]. Msg: {msg_texto}'
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            lista_itens = json.loads(limpo[limpo.find("["):limpo.rfind("]")+1])
            if len(lista_itens) > 0:
                pendencias_confirmacao[chat_id] = {"intencao": "contagem_fisica", "itens": lista_itens}
                botoes = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"✅ Sincronizar {len(lista_itens)} Itens", callback_data="conf_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_nao")
                ]])
                await update.message.reply_text(f"📦 **Contagem Detectada!** {len(lista_itens)} itens lidos. Confirmar?", reply_markup=botoes, parse_mode="Markdown")
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro ao ler estoque: `{e}`", parse_mode="Markdown")
            return

    # INTERCEPTAÇÃO FINANCEIRA
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "entrada"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(c.isdigit() for c in msg_texto):
        prompt = f'Extraia APENAS em JSON puro: {{"receita_bruta": num, "custos": num, "taxas": num, "unidade": "Bar Raio do Sol" ou "Fillara Cosméticos" ou "Linha Erótica", "data": "2026-10-27"}}. Msg: {msg_texto}'
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(limpo[limpo.find("{"):limpo.rfind("}")+1])
            receita = float(dados.get("receita_bruta", 0))
            if receita > 0:
                pendencias_confirmacao[chat_id] = {"intencao": "lancar_caixa_avancado", "receita_bruta": receita, "custos": float(dados.get("custos", 0)), "taxas": float(dados.get("taxas", 0)), "unidade": str(dados.get("unidade", "Bar Raio do Sol")), "data": "2026-10-27"}
                botoes = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Confirmar Lançamento", callback_data="conf_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_nao")
                ]])
                await update.message.reply_text(f"❓ **Confirma Lançamento?**\n💰 Receita: R$ {receita:.2f}\n🏢 {dados.get('unidade')}", reply_markup=botoes, parse_mode="Markdown")
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro no parser: `{e}`", parse_mode="Markdown")
            return

    await update.message.reply_text("💡 Utilize o menu guiado abaixo:", reply_markup=obter_menu_por_perfil(cargo), parse_mode="Markdown")

async def botoes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user = update.effective_user
    data = query.data

    dados_user = agente_usuarios.obter_ou_cadastrar_usuario(user.id, user.first_name)
    cargo = dados_user.get("cargo", "Cliente")

    # Ações do Menu
    if data == "menu_dre" and cargo == "Dono":
        botoes = InlineKeyboardMarkup([
            [InlineKeyboardButton("☀️ Bar Raio do Sol", callback_data="dre_bar")],
            [InlineKeyboardButton("💄 Fillara Cosméticos", callback_data="dre_fillara")],
            [InlineKeyboardButton("🔥 Linha Erótica", callback_data="dre_erotica")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]
        ])
        await query.edit_message_text("📊 **Escolha a unidade para consultar o DRE:**", reply_markup=botoes, parse_mode="Markdown")
        return

    elif data.startswith("dre_") and cargo == "Dono":
        unidade = "Bar Raio do Sol" if data == "dre_bar" else "Fillara Cosméticos" if data == "dre_fillara" else "Linha Erótica"
        res = orquestrador.processar_comando_orquestrado("consultar_dre", {"unidade": unidade})
        await query.edit_message_text(f"{res}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]]), parse_mode="Markdown")
        return

    elif data == "menu_estoque" and cargo in ["Dono", "Funcionario"]:
        res = orquestrador.processar_comando_orquestrado("consultar_estoque", {})
        await query.edit_message_text(f"{res}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]]), parse_mode="Markdown")
        return

    elif data == "menu_voltar":
        await start(update, context)
        return

    # Confirmação Sim/Não
    dado = pendencias_confirmacao.get(chat_id)
    if not dado:
        await query.edit_message_text("⚠️ Ação expirada.", reply_markup=obter_menu_por_perfil(cargo))
        return

    if data == "conf_sim":
        res = orquestrador.processar_comando_orquestrado(dado["intencao"], dado)
        msg_res = res.get('mensagem') if isinstance(res, dict) else str(res)
        await query.edit_message_text(f"✅ **Concluído!**\n{msg_res}", reply_markup=obter_menu_por_perfil(cargo))
        pendencias_confirmacao.pop(chat_id, None)

    elif data == "conf_nao":
        await query.edit_message_text("🚫 **Operação cancelada.**", reply_markup=obter_menu_por_perfil(cargo))
        pendencias_confirmacao.pop(chat_id, None)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, processar_mensagem))
    app.add_handler(CallbackQueryHandler(botoes_handler))
    app.run_polling()