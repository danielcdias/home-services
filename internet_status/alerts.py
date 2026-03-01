from django.conf import settings
from mailersend import MailerSendClient

from .models import InternetProvider, ConnectionSpeed, ConnectionStatus, StatusChoices


def send_alert_email(subject, text_content, to_emails):
    """Envia o e-mail usando a API oficial do MailerSend."""
    mailer = MailerSendClient(settings.MAILERSEND_API_KEY)

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
        print(f"E-mail enviado com sucesso: {subject}")
        return response
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return None


# --- Lógica de Verificação (Gatilhos) ---

def check_and_alert_speed(provider_id):
    """Verifica quedas de velocidade e dispara alertas."""
    provider = InternetProvider.objects.get(id=provider_id)
    emails_destino = provider.destination_emails_list

    if not emails_destino or provider.speed_drop_limit <= 0:
        return  # Sem e-mails configurados ou limite desativado

    limit = provider.speed_drop_limit
    last_tests = ConnectionSpeed.objects.filter(
        provider=provider).order_by('-last_tested')[:limit]

    if len(last_tests) < limit:
        return  # Ainda não há testes suficientes no banco

    # Verifica se TODOS os últimos 'X' testes estão abaixo de 100 Mbps
    all_below_100 = all(test.download_speed < 100.0 for test in last_tests)

    if all_below_100 and not provider.speed_alert_active:
        # Dispara o alerta de queda
        subject = f"⚠️ ALERTA: Velocidade reduzida na interface ({provider.name})"
        body = (f"A velocidade de download caiu para menos de 100 Mbps nos últimos {limit} "
                f"testes consecutivos.\nÚltima velocidade registrada: "
                f"{last_tests[0].download_speed} Mbps.\nVerifique o cabo ou a interface "
                f"eth1 do dcd-router.")

        send_alert_email(subject, body, emails_destino)

        # Atualiza o estado para não gerar spam
        provider.speed_alert_active = True
        provider.save(update_fields=['speed_alert_active'])

    elif not all_below_100 and provider.speed_alert_active:
        # Se o alerta estava ativo, mas a velocidade mais recente voltou a >= 100, avisa que normalizou
        latest_test = last_tests[0]
        if latest_test.download_speed >= 100.0:
            subject = f"✅ NORMALIZADO: Velocidade da rede ({provider.name})"
            body = (f"A velocidade de rede voltou ao normal.\nÚltima velocidade "
                    f"registrada: {latest_test.download_speed} Mbps.")

            send_alert_email(subject, body, emails_destino)

            provider.speed_alert_active = False
            provider.save(update_fields=['speed_alert_active'])


def check_and_alert_connection(provider_id):
    """Verifica quedas de conectividade e dispara alertas."""
    provider = InternetProvider.objects.get(id=provider_id)
    emails_destino = provider.destination_emails_list

    if not emails_destino or provider.connection_drop_limit <= 0:
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
                f"testes consecutivos.\nVerifique o link do provedor.")

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
