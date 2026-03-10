import json
import schedule
import time
import threading
from pathlib import Path
from datetime import datetime

from croniter import croniter

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string
from internet_status.models import InternetProvider

def run_threaded(job_func, *args, **kwargs):
    """
    Função auxiliar que executa a tarefa real dentro de uma nova Thread.
    """
    job_thread = threading.Thread(target=job_func, args=args, kwargs=kwargs)
    job_thread.start()

class Command(BaseCommand):
    help = 'Executa o agendador híbrido com reload dinâmico e execução em multithreading'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cron_tasks = []  # Lista para armazenar as tarefas CRON ativas

    def load_tasks(self):
        """Limpa a agenda atual e recarrega do JSON e do Banco de Dados."""
        schedule.clear()
        self.cron_tasks.clear()
        self.stdout.write(self.style.WARNING("Limpando agendamentos antigos..."))

        json_path = Path(settings.BASE_DIR) / 'scheduled-tasks.json'

        # --- 1. CARGA ESTÁTICA (JSON) ---
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                tasks_config = json.load(f)

            self.stdout.write(self.style.SUCCESS("Carregando tarefas estáticas (JSON)..."))
            for config in tasks_config:
                task_path = config.get('task')
                try:
                    task_func = import_string(task_path)
                except ImportError:
                    self.stdout.write(self.style.ERROR(f"Falha ao importar a tarefa: {task_path}"))
                    continue

                sched_type = config.get('type')
                if sched_type == 'interval':
                    value = config.get('value')
                    unit = config.get('unit')

                    if unit == 'minutes':
                        schedule.every(value).minutes.do(run_threaded, task_func)
                    elif unit == 'hours':
                        schedule.every(value).hours.do(run_threaded, task_func)
                    self.stdout.write(f" -> [JSON] {task_path} (A cada {value} {unit} - background)")

                elif sched_type == 'daily':
                    run_time = config.get('time')
                    schedule.every().day.at(run_time).do(run_threaded, task_func)
                    self.stdout.write(f" -> [JSON] {task_path} (Diariamente às {run_time} - background)")

        # --- 2. CARGA DINÂMICA (BASE DE DADOS - CRON) ---
        self.stdout.write(self.style.SUCCESS("Carregando tarefas dinâmicas (Base de Dados com CRON)..."))
        try:
            ping_task = import_string('internet_status.tasks.check_internet_status')
            speed_task = import_string('internet_status.tasks.check_internet_speed')

            providers = InternetProvider.objects.filter(enabled=True)
            now = datetime.now()
            
            for provider in providers:
                # Carregar tarefa de Ping
                if provider.status_check_interval and croniter.is_valid(provider.status_check_interval):
                    cron_obj = croniter(provider.status_check_interval, now)
                    self.cron_tasks.append({
                        'func': ping_task,
                        'kwargs': {'provider_id': provider.id},
                        'cron_obj': cron_obj,
                        'next_run': cron_obj.get_next(datetime)
                    })
                    self.stdout.write(f" -> [BD] Ping p/ '{provider.name}' (CRON: {provider.status_check_interval})")

                # Carregar tarefa de Speedtest
                if provider.speed_test_interval and croniter.is_valid(provider.speed_test_interval):
                    cron_obj = croniter(provider.speed_test_interval, now)
                    self.cron_tasks.append({
                        'func': speed_task,
                        'kwargs': {'provider_id': provider.id},
                        'cron_obj': cron_obj,
                        'next_run': cron_obj.get_next(datetime)
                    })
                    self.stdout.write(f" -> [BD] Speedtest p/ '{provider.name}' (CRON: {provider.speed_test_interval})")
                    
        except Exception as ex:
            self.stdout.write(self.style.ERROR(f"Erro ao carregar da base de dados: {ex}"))

    def run_cron_tasks(self):
        """Avalia e executa as tarefas baseadas em expressões CRON."""
        now = datetime.now()
        for task in self.cron_tasks:
            if now >= task['next_run']:
                run_threaded(task['func'], **task['kwargs'])
                # Atualiza a data da próxima execução
                task['next_run'] = task['cron_obj'].get_next(datetime)

    def handle(self, *args, **options):
        heartbeat_file = Path(settings.BASE_DIR) / 'scheduler_heartbeat.lock' if getattr(
            settings, 'LOCAL_DEV_ENV', False) else Path('/tmp/scheduler_heartbeat.lock')
        shared_dir = Path(settings.BASE_DIR) / 'shared'
        shared_dir.mkdir(exist_ok=True)
        reload_flag = shared_dir / 'reload_scheduler.flag'

        if heartbeat_file.exists():
            heartbeat_file.unlink()
        if reload_flag.exists():
            reload_flag.unlink()

        self.stdout.write(self.style.SUCCESS("Iniciando Agendador Híbrido Multithread com Reload Dinâmico..."))
        self.load_tasks()
        self.stdout.write(self.style.SUCCESS("\nAgendador a correr. A aguardar tarefas..."))

        try:
            while True:
                if reload_flag.exists():
                    self.stdout.write(self.style.WARNING("\nDetectada alteração nas configurações! A recarregar..."))
                    reload_flag.unlink()
                    self.load_tasks()

                # Avalia as tarefas estáticas
                schedule.run_pending()
                # Avalia as nossas novas tarefas dinâmicas CRON
                self.run_cron_tasks()

                heartbeat_file.touch(exist_ok=True)
                time.sleep(2)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nAgendador encerrado."))
