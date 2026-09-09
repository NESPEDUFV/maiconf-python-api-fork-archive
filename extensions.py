import redis
from rq import Queue

import config

# Mesma conexão (host/porta/TLS) que o BullModule do mymobiconfapi monta —
# reutiliza o Redis existente (mmc-redis em dev, ElastiCache em prod) em vez
# de uma instância dedicada. RQ usa o prefixo de chaves "rq:*", então convive
# na mesma instância sem colidir com as filas BullMQ ("bull:*") do Node.
_redis_kwargs = {"host": config.AWS_REDIS_HOST, "port": int(config.AWS_REDIS_PORT)}
if config.SSL_ENABLED:
    _redis_kwargs["ssl"] = True
    _redis_kwargs["ssl_cert_reqs"] = None

redis_conn = redis.Redis(**_redis_kwargs)

# Fila de processamento pesado (extração de atividades). Roda em containers
# de worker separados da API — ver worker.py e capabilities/extrator_atividades/tasks.py.
extrator_atividades_queue = Queue("extrator_atividades", connection=redis_conn)

# Mesmo nome de fila usado pelo maiconfpayment (notifications_egress) para a
# entrega assinada de webhooks — ver notifications/.
notifications_egress_queue = Queue("notifications_egress", connection=redis_conn)
