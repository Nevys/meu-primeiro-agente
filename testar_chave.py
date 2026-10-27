import requests

GROQ_API_KEY = "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".strip()
URL_MODELOS = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

try:
    resposta = requests.get(URL_MODELOS, headers=headers, timeout=10)
    print(f"STATUS HTTP: {resposta.status_code}")
    print(f"RESPOSTA GROQ: {resposta.text}")
except Exception as e:
    print(f"ERRO DE CONEXÃO: {e}")