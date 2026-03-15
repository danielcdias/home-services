import logging

from django.conf import settings
from mailersend import MailerSendClient

from .models import InternetProvider, ConnectionSpeed, ConnectionStatus, StatusChoices


logger = logging.getLogger(__name__)


def send_alert_email(subject, text_content, to_emails):
    """Envia o e-mail usando a API oficial do MailerSend."""
    api_key = getattr(settings, 'MAILERSEND_API_KEY', None)

    # Se a chave de API não existir (ex: ambiente de desenvolvimento), 
    # aborta o envio graciosamente sem causar erro (crash) no sistema.
    if not api_key:
        logger.warning(f"Alerta ignorado: Chave MAILERSEND_API_KEY não configurada. Assunto: '{subject}'")
        return None

    try:
        mailer = MailerSendClient(api_key)
    except ValueError as e:
        logger.error(f"Erro de configuração do MailerSend: {e}")
        return None

    # Formata a lista de destinatários para o padrão do MailerSend
    recipients = [{"name": "Admin", "email": email} for email in to_emails]

    # Estrutura do payload conforme o novo padrão da biblioteca
    email_params = {
        "from": {
            "email": settings.SENDER_EMAIL,
            "name": settings.SENDER_NAME
        },
        "to": recipients,
        "subject": subject,
        "text": text_content
    }

    try:
        response = mailer.emails.send(email_params)
        logger.info(f"E-mail enviado com sucesso: {subject}")
        return response
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return None


# --- Lógica de Verificação (Gatilhos) ---

def check_and_alert_speed(provider_id):
    """Verifica quedas de velocidade e dispara alertas."""
    provider = InternetProvider.objects.get(id=provider_id)
    emails_destino = [e.strip() for e in provider.destination_emails.split(',') if e.strip()]

    if not emails_destino:
        return

    limit = provider.speed_drop_limit
    last_tests = ConnectionSpeed.objects.filter(
        provider=provider).order_by('-last_tested')[:limit]

    # Só avalia se já tiver testes suficientes armazenados
    if len(last_tests) < limit:
        return

    # Verifica se TODOS os últimos 'X' testes estão abaixo do mínimo aceitável
    all_bad = True
    for test in last_tests:
        if (test.download_speed >= provider.download_speed_minimum_threshold and
                test.upload_speed >= provider.upload_speed_minimum_threshold):
            all_bad = False
            break

    # Se todos estiverem maus e o alerta ainda não foi ativado
    if all_bad and not provider.speed_alert_active:
        subject = f"🚨 ALERTA: Queda de Velocidade de Internet ({provider.name})"
        body = (f"A velocidade da internet esteve abaixo do limite mínimo aceitável nos últimos {limit} testes.\\n"
                f"Último Download: {last_tests[0].download_speed} Mbps\\n"
                f"Último Upload: {last_tests[0].upload_speed} Mbps")

        send_alert_email(subject, body, emails_destino)

        # Marca que o alerta foi acionado para não fazer spam
        provider.speed_alert_active = True
        provider.save(update_fields=['speed_alert_active'])

    # Se o alerta estava ativo, mas a internet já normalizou no último teste
    elif not all_bad and provider.speed_alert_active:
        latest_test = last_tests[0]
        if (latest_test.download_speed >= provider.download_speed_minimum_threshold and
                latest_test.upload_speed >= provider.upload_speed_minimum_threshold):
            
            subject = f"✅ NORMALIZADO: Velocidade de Internet ({provider.name})"
            body = (f"A velocidade da internet voltou ao normal.\\n"
                    f"Download Atual: {latest_test.download_speed} Mbps\\n"
                    f"Upload Atual: {latest_test.upload_speed} Mbps")

            send_alert_email(subject, body, emails_destino)

            # Desativa o alerta
            provider.speed_alert_active = False
            provider.save(update_fields=['speed_alert_active'])


def check_and_alert_connection(provider_id):
    """Verifica falhas de ping (conectividade) e dispara alertas."""
    provider = InternetProvider.objects.get(id=provider_id)
    emails_destino = [e.strip() for e in provider.destination_emails.split(',') if e.strip()]

    if not emails_destino:
        return

    limit = provider.connection_drop_limit
    last_tests = ConnectionStatus.objects.filter(
        provider=provider).order_by('-last_checked')[:limit]

    if len(last_tests) < limit:
        return

    # Verifica se TODOS os últimos 'Y' testes estão instáveis ou desconectados
    bad_statuses = [StatusChoices.UNSTABLE, StatusChoices.DISCONNECTED]
    all_bad = all(test.status in bad_statuses for test in last_tests)

    if all_bad and not provider.connection_alert_active:
        subject = f"🚨 ALERTA: Queda ou Instabilidade de Internet ({provider.name})"
        body = (f"A conexão falhou ou apresentou instabilidade nos últimos {limit} "
                f"testes consecutivos.\\nVerifique o link do provedor.")

        send_alert_email(subject, body, emails_destino)

        provider.connection_alert_active = True
        provider.save(update_fields=['connection_alert_active'])

    elif not all_bad and provider.connection_alert_active:
        # Se normalizou (o último teste é CONNECTED)
        latest_test = last_tests[0]
        if latest_test.status == StatusChoices.CONNECTED:
            subject = f"🌐 NORMALIZADO: Conexão de Internet ({provider.name})"
            body = (f"A conexão de internet foi restabelecida e os pings estão "
                    f"respondendo normalmente.")

            send_alert_email(subject, body, emails_destino)

            provider.connection_alert_active = False
            provider.save(update_fields=['connection_alert_active'])
