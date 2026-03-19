import json

from django.core.management.base import BaseCommand
from django.core import serializers
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User

from internet_status.models import (
    InternetProvider, HostsToPing, ConnectionStatus, 
    ConnectionSpeed, DailyStatusSummary, DailySpeedSummary
)


class Command(BaseCommand):
    help = 'Gera um dump inteligente: logs filtrados por data e cadastros/resumos completos.'

    def add_arguments(self, parser):
        parser.add_argument('--since', type=str, help='Data inicial no formato YYYY-MM-DD')

    def handle(self, *args, **options):
        date_str = options.get('since')
        start_date = parse_date(date_str) if date_str else None

        objects = []

        # 1. Cadastros Base e Usuários (Sempre completos)
        objects.extend(User.objects.all())
        objects.extend(InternetProvider.objects.all())
        objects.extend(HostsToPing.objects.all())

        # 2. Resumos Diários (Sempre completos para manter o histórico consolidado)
        objects.extend(DailyStatusSummary.objects.all())
        objects.extend(DailySpeedSummary.objects.all())

        # 3. Dados de Verificação (Brutos) - Filtrados por data
        if start_date:
            # Filtra registros a partir da data informada
            objects.extend(ConnectionStatus.objects.filter(last_checked__date__gte=start_date))
            objects.extend(ConnectionSpeed.objects.filter(last_tested__date__gte=start_date))
        else:
            # Se não informar data, traz tudo (comportamento original)
            objects.extend(ConnectionStatus.objects.all())
            objects.extend(ConnectionSpeed.objects.all())

        # Serialização com chaves naturais para evitar conflitos entre IDs de bancos diferentes (Postgres -> SQLite)
        data = serializers.serialize(
            "json", 
            objects, 
            indent=4, 
            use_natural_foreign_keys=True, 
            use_natural_primary_keys=True
        )
        
        self.stdout.write(data)
