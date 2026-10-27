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
def home(): return "☀️ Bot ERP Raio do Sol Operacional!"

def rodar_servidor_web(): web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=rodar_servidor_web, daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8734618901:AAHCaSkMyUZpDRO2iuAR0Ym8vu15beUJxO8").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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").strip()

pendencias_confirmacao = {}

def obter_menu_por_perfil(cargo):
    """Gera menus dinâmicos ocultando o teste para quem não for Dono."""
    botoes = []
    
    if cargo == "Dono":
        botoes.append([InlineKeyboardButton("📊 DRE Completo por Unidade", callback_data="menu_dre")])
        botoes.append([InlineKeyboardButton("📦 Auditoria de Estoque (COO)", callback_data="menu_estoque")])
        botoes.append([InlineKeyboardButton("📝 Instrução de Contagem Física", callback_data="menu_contagem_instrucao")])
        botoes.append([InlineKeyboardButton("💵 Como Lançar Venda/Caixa", callback_data="menu_venda_instrucao")])
        # Botão exclusivo do Dono
        botoes.append([InlineKeyboardButton("🧪 [DONO] Injetar Dados de Teste", callback_data="menu_popular")])
        
    elif cargo == "Funcionario":
        botoes.append([InlineKeyboardButton("📦 Instrução para Contagem de Estoque", callback_data="menu_contagem_instrucao")])
        botoes.append([InlineKeyboardButton("💵 Como Registrar Venda do Turno", callback_data="menu_venda_instrucao")])
        botoes.append([InlineKeyboardButton("📦 Consultar Rupturas de Estoque", callback_data="menu_estoque")])
        
    else:  # Cliente
        botoes.append([InlineKeyboardButton("💄 Catálogo Fillara Cosméticos", callback_data="cliente_fillara")])
        botoes.append([InlineKeyboardButton("☀️ Cardápio Bar Raio do Sol", callback_data="cliente_bar")])
        botoes.append([InlineKeyboardButton("🔥 Linha Erótica", callback_data="cliente_erotica")])
        botoes.append([InlineKeyboardButton("💬 Falar com Atendente", callback_data="cliente_atendente")])

    return InlineKeyboardMarkup(botoes)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    dados_user = agente_usuarios.obter_ou_cadastrar_usuario(user.id, user.first_name)
    cargo = dados_user.get("cargo", "Cliente")

    msg = (
        f"☀️ **Diretoria Virtual - Bar Raio do Sol, Fillara & Linha Erótica**\n\n"
        f"👤 **Usuário:** {user.first_name} | **Perfil:** `{cargo}`\n\n"
        f"Selecione uma opção abaixo:"
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

    if cargo == "Cliente":
        res_ia = consultar_groq(
            "Você é a atendente virtual do Bar Raio do Sol, Fillara Cosméticos e Linha Erótica. Seja simpática e ajude com dúvidas de compras.", 
            f"Cliente {user.first_name}: {msg_texto}"
        )
        await update.message.reply_text(res_ia)
        return

    msg_lower = msg_texto.lower()

    # 1. INTERCEPTAÇÃO DE CONTAGEM FÍSICA POR TEXTO (Prateleira, Geladeira, Freezer, Palete)
    gatilhos_estoque = ["prateleira", "pratileira", "geladeira", "freezer", "frezer", "palete"]
    if any(k in msg_lower for k in gatilhos_estoque) and "-" in msg_texto:
        prompt = (
            "O usuário enviou uma contagem física contendo seções (Prateleira, Geladeira, Freezer, Palete) e itens com quantidades (ex: Heineken - 19). "
            "Para cada item, identifique o produto, a quantidade (número inteiro ou decimal) e o local correto onde ele está (Prateleira, Geladeira, Freezer ou Palete). "
            "Retorne APENAS um JSON puro no formato de lista de objetos: "
            '[{"produto": "nome do produto", "quantidade": numero, "local": "Prateleira/Geladeira/Freezer/Palete"}]. '
            f"Mensagem enviada: {msg_texto}"
        )
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            lista_itens = json.loads(limpo[limpo.find("["):limpo.rfind("]")+1])
            
            if len(lista_itens) > 0:
                pendencias_confirmacao[chat_id] = {"intencao": "contagem_fisica", "itens": lista_itens}
                
                resumo = "\n".join([f"• {i['produto']} ({i.get('local', 'Geral')}): {i['quantidade']} un." for i in lista_itens[:6]])
                if len(lista_itens) > 6: resumo += f"\n... e mais {len(lista_itens)-6} itens."

                botoes = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"✅ Sincronizar {len(lista_itens)} Itens no Airtable", callback_data="conf_sim"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="conf_nao")
                ]])
                
                await update.message.reply_text(
                    f"📦 **Contagem Física de Estoque Detectada!**\n\nResumo da leitura:\n{resumo}\n\nDeseja enviar esta contagem ao COO para atualizar o Airtable?",
                    reply_markup=botoes, parse_mode="Markdown"
                )
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ **Erro ao interpretar contagem:** `{e}`\nRetorno IA: `{json_resp}`", parse_mode="Markdown")
            return

    # 2. INTERCEPTAÇÃO DE LANÇAMENTOS FINANCEIROS / CAIXA
    gatilhos_caixa = ["registra", "lança", "venda", "vendi", "entrada"]
    if any(k in msg_lower for k in gatilhos_caixa) and any(c.isdigit() for c in msg_texto):
        prompt = f'Extraia APENAS em JSON puro: {{"receita_bruta": num, "custos": num, "taxas": num, "unidade": "Bar Raio do Sol" ou "Fillara Cosméticos" ou "Linha Erótica", "data": "2026-10-27"}}. Msg: {msg_texto}'
        json_resp = consultar_groq(prompt)
        try:
            limpo = json_resp.replace("```json", "").replace("```", "").strip()
            dados = json.loads(limpo[limpo.find("{"):limpo.rfind("}")+1])
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
                    f"❓ **Confirma Lançamento?**\n\n🏢 Unidade: {dados.get('unidade')}\n💰 Receita: R$ {receita:.2f}\n💸 Custos: R$ {dados.get('custos', 0):.2f}", 
                    reply_markup=botoes, parse_mode="Markdown"
                )
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro no parser de caixa: `{e}`", parse_mode="Markdown")
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

    elif data == "menu_contagem_instrucao":
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]])
        await query.edit_message_text(
            "📦 **Como enviar a Contagem de Estoque:**\n\nBasta colar sua lista diária no chat. Exemplo:\n\n"
            "*Prateleira*\nVodka Smirnoff - 1\nVinho Don Bosco - 4\n\n*Geladeira*\nHeineken - 19\n\n*Freezer*\nLitrão Itaipava - 40\n\n"
            "O bot processará os locais e criará o botão para sincronizar com o Airtable automaticamente!",
            reply_markup=botoes, parse_mode="Markdown"
        )
        return

    elif data == "menu_venda_instrucao":
        botoes = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]])
        await query.edit_message_text(
            "💵 **Como registrar uma venda:**\n\nEnvie uma mensagem direta no chat informando os valores. Exemplo:\n\n"
            "• *'Vendi 150 com custo 50 no bar'*\n• *'Registra entrada de 1200 na Fillara'*\n\nO bot calculará o lucro e exibirá o botão de confirmação.",
            reply_markup=botoes, parse_mode="Markdown"
        )
        return

    elif data == "menu_popular" and cargo == "Dono":
        res = orquestrador.processar_comando_orquestrado("popular_dados", {})
        msg_pop = res.get('mensagem') if isinstance(res, dict) else str(res)
        await query.edit_message_text(f"🧪 **Injeção de Teste:**\n{msg_pop}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_voltar")]]), parse_mode="Markdown")
        return

    elif data == "menu_voltar":
        await start(update, context)
        return

    # Confirmação Sim / Não
    dado = pendencias_confirmacao.get(chat_id)
    if not dado:
        await query.edit_message_text("⚠️ Ação expirada.", reply_markup=obter_menu_por_perfil(cargo))
        return

    if data == "conf_sim":
        res = orquestrador.processar_comando_orquestrado(dado["intencao"], dado)
        msg_res = res.get('mensagem') if isinstance(res, dict) else str(res)
        await query.edit_message_text(f"✅ **Concluído com Sucesso!**\n{msg_res}", reply_markup=obter_menu_por_perfil(cargo))
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