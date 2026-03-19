import json
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
        self.cron_tasks = []

    def load_tasks(self):
        """Limpa a agenda atual e recarrega do JSON e do Banco de Dados usando CRON."""
        self.cron_tasks.clear()
        self.stdout.write(self.style.WARNING("Limpando agendamentos antigos..."))

        json_path = Path(settings.BASE_DIR) / 'scheduled-tasks.json'
        now = datetime.now()

        # --- 1. CARGA ESTÁTICA (JSON) ---
        self.stdout.write(self.style.SUCCESS("Carregando tarefas estáticas (JSON)..."))
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    for task in tasks:
                        try:
                            job_func = import_string(task['task'])
                            cron_expr = task['schedule']
                            
                            self.cron_tasks.append({
                                'name': task['name'],
                                'cron_obj': croniter(cron_expr, now),
                                'next_run': croniter(cron_expr, now).get_next(datetime),
                                'last_run_minute': None, # Controle de duplicidade
                                'func': job_func,
                                'args': [],
                                'kwargs': {},
                                'source': 'JSON'
                            })
                            self.stdout.write(f" -> [JSON] {task['name']} (CRON: {cron_expr})")
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Falha ao importar tarefa JSON '{task.get('name')}': {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao ler scheduled-tasks.json: {e}"))

        # --- 2. CARGA DINÂMICA (BANCO DE DADOS) ---
        self.stdout.write(self.style.SUCCESS("Carregando tarefas dinâmicas (Base de Dados com CRON)..."))
        try:
            providers = InternetProvider.objects.filter(enabled=True)
            for provider in providers:
                # Status Check
                self.cron_tasks.append({
                    'name': f"Ping p/ '{provider.name}'",
                    'cron_obj': croniter(provider.status_check_interval, now),
                    'next_run': croniter(provider.status_check_interval, now).get_next(datetime),
                    'last_run_minute': None,
                    'func': import_string('internet_status.tasks.check_internet_status'),
                    'args': [provider.id],
                    'kwargs': {},
                    'source': 'BD'
                })
                self.stdout.write(f" -> [BD] Ping p/ '{provider.name}' (CRON: {provider.status_check_interval})")

                # Speed Test
                self.cron_tasks.append({
                    'name': f"Speedtest p/ '{provider.name}'",
                    'cron_obj': croniter(provider.speed_test_interval, now),
                    'next_run': croniter(provider.speed_test_interval, now).get_next(datetime),
                    'last_run_minute': None,
                    'func': import_string('internet_status.tasks.check_internet_speed'),
                    'args': [provider.id],
                    'kwargs': {},
                    'source': 'BD'
                })
                self.stdout.write(f" -> [BD] Speedtest p/ '{provider.name}' (CRON: {provider.speed_test_interval})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao carregar tarefas do banco: {e}"))

    def run_cron_tasks(self):
        """Verifica quais tarefas CRON devem ser executadas agora."""
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)

        for task in self.cron_tasks:
            # Só executa se:
            # 1. O tempo atual passou ou igualou o next_run
            # 2. O minuto atual é diferente do minuto da última execução (impede duplicata no mesmo minuto)
            if now >= task['next_run'] and current_minute != task['last_run_minute']:
                
                # Registra a execução no minuto atual
                task['last_run_minute'] = current_minute
                # Calcula a próxima execução baseada no tempo de agora
                task['next_run'] = task['cron_obj'].get_next(datetime)
                
                self.stdout.write(self.style.NOTICE(f"Executando: {task['name']} [{task['source']}]"))
                run_threaded(task['func'], *task['args'], **task['kwargs'])

    def handle(self, *args, **options):
        # ... (mantenha a lógica do heartbeat e flag de reload idêntica)
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

                self.run_cron_tasks()

                with open(heartbeat_file, 'w') as f:
                    f.write(datetime.now().isoformat())
                
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nAgendador parado pelo usuário."))
            if heartbeat_file.exists():
                heartbeat_file.unlink()
