import sys
import requests
from datetime import datetime
import environ
from pathlib import Path

def send_test_email(recipient_email):
    # Inicializa o environ
    env = environ.Env()
    
    # Define o caminho base e procura o arquivo .env
    BASE_DIR = Path(__file__).resolve().parent
    env_file = BASE_DIR / '.env'
    
    # Lê o arquivo .env se ele existir no caminho
    if env_file.exists():
        environ.Env.read_env(env_file)

    # Coleta as variáveis de ambiente com o environ
    api_key = env('MAILERSEND_API_KEY', default=None)
    if not api_key:
        print("❌ Erro: A variável MAILERSEND_API_KEY não foi encontrada no ambiente ou no arquivo .env.")
        sys.exit(1)

    # IMPORTANTE: Substitua pelo e-mail do domínio verificado no seu painel do MailerSend
    sender_email = env('MAILERSEND_SENDER_EMAIL', default='seu-email-verificado@seudominio.com')

    url = "https://api.mailersend.com/v1/email"

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Authorization": f"Bearer {api_key}"
    }

    current_time = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    # Mantive a grafia exata que você pediu no corpo da mensagem
    body_text = f"E-mail enviado via MailterSend em {current_time}."

    payload = {
        "from": {
            "email": sender_email,
            "name": "Home Services App"
        },
        "to": [
            {
                "email": recipient_email
            }
        ],
        "subject": "[MailerSend] Teste",
        "text": body_text,
        "html": f"<p>{body_text}</p>"
    }

    print(f"Iniciando envio para {recipient_email} via MailerSend...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # O MailerSend geralmente retorna 202 (Accepted) quando o e-mail entra na fila
        if response.status_code in [200, 202]:
            print(f"✅ Sucesso! O e-mail foi enfileirado/enviado com sucesso (Status: {response.status_code}).")
        else:
            print(f"❌ Erro na API do MailerSend. Código de Status: {response.status_code}")
            print(f"Detalhes do erro: {response.text}")
            
    except Exception as e:
        print(f"❌ Falha de conexão ou erro interno: {e}")

if __name__ == "__main__":
    # Verifica se o e-mail foi passado como argumento na linha de comando
    if len(sys.argv) < 2:
        print("Uso incorreto. Siga o padrão:")
        print("python test_mailersend.py <endereco-de-email@destino.com>")
        sys.exit(1)
        
    target_email = sys.argv[1]
    send_test_email(target_email)
