from django.shortcuts import redirect
from django.urls import reverse
from django_otp import user_has_device

class Force2FASetupMiddleware:
    """
    Garante que qualquer usuário autenticado tenha o 2FA configurado.
    Caso contrário, ele fica 'preso' e é redirecionado para a tela de configuração.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Só verifica se o usuário já passou da tela de login (está autenticado)
        if request.user.is_authenticated:
            
            # Verifica se ele NÃO tem nenhum dispositivo 2FA cadastrado
            if not user_has_device(request.user):
                
                # Lista de URLs que o usuário "preso" TEM permissão para acessar
                allowed_paths = [
                    reverse('two_factor:setup'),
                    reverse('two_factor:qr'),
                    reverse('logout'),
                ]                

                # Se a página atual não for uma das permitidas, bloqueia e manda para o setup
                if request.path not in allowed_paths:
                    return redirect('two_factor:setup')

        return self.get_response(request)
    