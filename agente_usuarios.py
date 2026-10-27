import os
import requests

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "path6ehvNDRYCc82L.dd90138f1df27ae82eeba74cf6121218785c742460d24ec6828d7e0fde8046bd").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appjM48jtF1tccYVq").strip()

def obter_ou_cadastrar_usuario(telegram_id, nome_usuario):
    """
    Busca o perfil do usuário pelo Telegram ID no Airtable.
    Se não encontrar, cadastra automaticamente como 'Cliente'.
    """
    telegram_id_str = str(telegram_id)
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Usuarios"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    
    try:
        filter_formula = f"{{Telegram_ID}}='{telegram_id_str}'"
        res = requests.get(url, headers=headers, params={"filterByFormula": filter_formula}, timeout=15)
        
        if res.status_code == 200:
            records = res.json().get("records", [])
            if records:
                fields = records[0].get("fields", {})
                return {
                    "cargo": fields.get("Cargo", "Cliente"),
                    "nome": fields.get("Nome", nome_usuario),
                    "unidade": fields.get("Unidade", "Geral")
                }
        
        # Cadastra automaticamente se não existir
        payload = {
            "records": [{
                "fields": {
                    "Telegram_ID": telegram_id_str,
                    "Nome": nome_usuario,
                    "Cargo": "Cliente",
                    "Unidade": "Geral"
                }
            }]
        }
        post_headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
        requests.post(url, headers=post_headers, json=payload, timeout=15)
        
        return {"cargo": "Cliente", "nome": nome_usuario, "unidade": "Geral"}

    except Exception as e:
        print(f"Erro na gestão de usuários: {e}")
        return {"cargo": "Cliente", "nome": nome_usuario, "unidade": "Geral"}