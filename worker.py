import logging
import sys

from rq import Worker

from extensions import redis_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    # Uso: python worker.py <fila> [<fila> ...]
    # ex.: python worker.py extrator_atividades
    #      python worker.py notifications_egress
    queue_names = sys.argv[1:] or ["extrator_atividades"]
    Worker(queue_names, connection=redis_conn).work()
