
import os

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.management.commands import createsuperuser

USER_ENV = os.environ['DJANGO_SUPERUSER_USERNAME']


class Command(createsuperuser.Command):
    help = "Cria um novo usuário admin, extendendo a criação padrão, porém não retorna erro caso o usuário já exista."

    def handle(self, *args, **options):
        if USER_ENV:
            user_not_found = True
            try:
                user = User.objects.get(username=USER_ENV)
                if user:
                    user_not_found = False
            except ObjectDoesNotExist:
                pass
            if user_not_found:
                super().handle(*args, **options)
            else:
                self.stdout.write(self.style.SUCCESS(
                    'O usuário admin já foi criado.'))
