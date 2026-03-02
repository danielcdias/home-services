import json
import schedule
import time

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from internet_status.models import InternetProvider


class Command(BaseCommand):
    help = 'Executa o agendador híbrido com reload dinâmico via flag'

    def load_tasks(self):
        """Limpa a agenda atual e recarrega do JSON e do Banco de Dados."""
        schedule.clear()
        self.stdout.write(self.style.WARNING(
            "Limpando agendamentos antigos..."))

        json_path = Path(settings.BASE_DIR) / 'scheduled-tasks.json'

        # --- 1. CARGA ESTÁTICA (JSON) ---
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                tasks_config = json.load(f)

            self.stdout.write(self.style.SUCCESS(
                "Carregando tarefas estáticas (JSON)..."))
            for config in tasks_config:
                task_path = config.get('task')
                try:
                    task_func = import_string(task_path)
                except ImportError as ex:
                    self.stdout.write(self.style.ERROR(
                        f"Falha ao importar a tarefa: {task_path}"))
                    continue

                sched_type = config.get('type')
                if sched_type == 'interval':
                    value = config.get('value')
                    unit = config.get('unit')

                    if unit == 'minutes':
                        schedule.every(value).minutes.do(task_func)
                    elif unit == 'hours':
                        schedule.every(value).hours.do(task_func)
                    self.stdout.write(
                        f" -> [JSON] {task_path} (A cada {value} {unit})")

                elif sched_type == 'daily':
                    run_time = config.get('time')
                    schedule.every().day.at(run_time).do(task_func)
                    self.stdout.write(
                        f" -> [JSON] {task_path} (Diariamente às {run_time})")
        else:
            self.stdout.write(
                f"Arquivo de configuração JSON não encontrado: {json_path}."
                f" Ignorando tarefas estáticas.")

        # --- 2. CARGA DINÂMICA (BANCO DE DADOS) ---
        self.stdout.write(self.style.SUCCESS(
            "Carregando tarefas dinâmicas (Banco de Dados)..."))
        try:
            ping_task = import_string(
                'internet_status.tasks.check_internet_status')
            speed_task = import_string(
                'internet_status.tasks.check_internet_speed')

            providers = InternetProvider.objects.filter(enabled=True)
            for provider in providers:
                if provider.status_check_interval > 0:
                    schedule.every(provider.status_check_interval).minutes.do(
                        ping_task, provider_id=provider.id)
                    self.stdout.write(
                        f" -> [BD] Ping p/ '{provider.name}' (A cada {provider.status_check_interval} min)")

                if provider.speed_test_interval > 0:
                    schedule.every(provider.speed_test_interval).minutes.do(
                        speed_task, provider_id=provider.id)
                    self.stdout.write(
                        f" -> [BD] Speedtest p/ '{provider.name}' (A cada {provider.speed_test_interval} min)")
        except Exception as ex:
            self.stdout.write(self.style.ERROR(
                f"Erro ao carregar do banco de dados: {ex}"))

    def handle(self, *args, **options):
        heartbeat_file = Path(settings.BASE_DIR) / 'scheduler_heartbeat.lock' if getattr(
            settings, 'LOCAL_DEV_ENV', False) else Path('/tmp/scheduler_heartbeat.lock')
        reload_flag = Path(settings.BASE_DIR) / 'reload_scheduler.flag'

        # Limpa os arquivos residuais na inicialização
        if heartbeat_file.exists():
            heartbeat_file.unlink()
        if reload_flag.exists():
            reload_flag.unlink()

        self.stdout.write(self.style.SUCCESS(
            "Iniciando Agendador Híbrido com Reload Dinâmico..."))

        # Faz a primeira carga
        self.load_tasks()

        self.stdout.write(self.style.SUCCESS(
            "\nAgendador rodando. Aguardando tarefas..."))

        try:
            while True:
                # Verifica se houve alteração no painel Admin (flag criada)
                if reload_flag.exists():
                    self.stdout.write(self.style.WARNING(
                        "\nDetectada alteração nas configurações! Recarregando..."))
                    reload_flag.unlink()  # Deleta a flag para não ficar em loop infinito
                    self.load_tasks()

                schedule.run_pending()
                heartbeat_file.touch(exist_ok=True)
                time.sleep(2)  # Pausa curta para não onerar o processador
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nAgendador encerrado."))
