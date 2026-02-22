import json
import schedule
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string
from pathlib import Path


class Command(BaseCommand):
    help = 'Executa o agendador de tarefas dinâmico baseado em JSON'

    def handle(self, *args, **options):
        heartbeat_file = settings.BASE_DIR / \
            'scheduled-tasks.json' if settings.DEBUG else Path(
                '/tmp/scheduler_heartbeat.txt')
        json_path = settings.BASE_DIR / 'scheduled-tasks.json'

        if not json_path.exists():
            raise CommandError(
                f"Arquivo de configuração não encontrado: {json_path}")

        # Carrega as configurações do JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            tasks_config = json.load(f)

        self.stdout.write(self.style.SUCCESS(
            "Carregando tarefas agendadas..."))

        for config in tasks_config:
            task_path = config.get('task')
            try:
                # Importa a função da task dinamicamente a partir da string
                task_func = import_string(task_path)
            except ImportError as ex:
                self.stdout.write(self.style.ERROR(
                    f"Falha ao importar a tarefa: {task_path}, exceção: {ex}"))
                continue

            sched_type = config.get('type')

            # Lógica de Agendamento por Intervalo (Minutos/Horas)
            if sched_type == 'interval':
                value = config.get('value')
                unit = config.get('unit')

                if unit == 'minutes':
                    schedule.every(value).minutes.do(task_func.enqueue)
                    self.stdout.write(
                        f" -> [OK] {task_path} (A cada {value} minutos)")
                elif unit == 'hours':
                    schedule.every(value).hours.do(task_func.enqueue)
                    self.stdout.write(
                        f" -> [OK] {task_path} (A cada {value} horas)")

            # Lógica de Agendamento Diário (Horário Específico)
            elif sched_type == 'daily':
                run_time = config.get('time')
                schedule.every().day.at(run_time).do(task_func.enqueue)
                self.stdout.write(
                    f" -> [OK] {task_path} (Diariamente às {run_time})")

        self.stdout.write(self.style.SUCCESS(
            "\nAgendador dinâmico rodando. Aguardando tarefas..."))

        # Loop infinito com Heartbeat para o Docker Healthcheck
        try:
            while True:
                schedule.run_pending()
                heartbeat_file.touch()
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nAgendador encerrado."))
