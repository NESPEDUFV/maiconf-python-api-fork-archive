import logging
import os

import config
from notifications.outgoing import enqueue_delivery

from . import pipeline

logger = logging.getLogger(__name__)


def process_extraction(
    file_path: str,
    original_filename: str,
    webhook_url: str = None,
    evento_id: str = None,
) -> dict:
    """
    Executado pelo worker da fila `extrator_atividades` (ver worker.py).

    Mesmo pipeline usado por POST /extract, mas fora do ciclo síncrono de
    request/response — pensado para arquivos grandes, onde a extração +
    chamada à LLM pode ultrapassar o tempo aceitável de uma requisição HTTP.
    Ao terminar, se houver um `webhook_url` (ou DASHBOARD_WEBHOOK_URL
    configurado), o resultado é entregue por webhook via
    `notifications.outgoing.enqueue_delivery` — mesmo mecanismo de entrega
    assinada usado pelo maiconfpayment.
    """
    target = webhook_url or config.DASHBOARD_WEBHOOK_URL

    try:
        resultado = pipeline.run_pipeline(file_path, original_filename)

        if target:
            enqueue_delivery(
                target_url=target,
                event_type="extrator_atividades.concluido",
                payload={"evento_id": evento_id, "arquivo": original_filename, **resultado},
            )

        return resultado
    except Exception as exc:
        logger.error("Falha ao processar extração de '%s': %s", original_filename, exc)
        if target:
            enqueue_delivery(
                target_url=target,
                event_type="extrator_atividades.falhou",
                payload={"evento_id": evento_id, "arquivo": original_filename, "erro": str(exc)},
            )
        raise
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as cleanup_err:
            logger.error("Falha ao remover arquivo temporário '%s': %s", file_path, cleanup_err)
