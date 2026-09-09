import hashlib
import hmac
import json
import logging

import requests

import config
from notifications.status import NotificationStatus

logger = logging.getLogger(__name__)


def _assinar(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def deliver_webhook(target_url: str, payload: dict, notification_id: str) -> None:
    """
    Executado pelo worker da fila `notifications_egress`.

    Mesmo contrato de assinatura usado pelo maiconfpayment para notificar o
    mymobiconfapi: corpo serializado uma única vez, HMAC-SHA256 no header
    `x-webhook-signature` (segredo IA_WEBHOOK_SECRET). Uma exceção aqui é
    capturada pelo `Retry` configurado em `enqueue_delivery` — RQ reagenda o
    job (RETRYING) até esgotar as tentativas, quando ele cai na fila de jobs
    falhos do próprio RQ (equivalente ao DEAD do maiconfpayment). Persistir
    esse histórico numa tabela própria, como o maiconfpayment faz com
    InternalNotification, é o próximo passo natural se for preciso auditoria.
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-internal-event-id": notification_id,
    }

    if config.IA_WEBHOOK_SECRET:
        headers["x-webhook-signature"] = _assinar(body, config.IA_WEBHOOK_SECRET)
    else:
        logger.error(
            "IA_WEBHOOK_SECRET não configurado — notificação [%s] será enviada sem assinatura "
            "e provavelmente rejeitada pelo receptor.",
            notification_id,
        )

    logger.info(">>> Disparando notificação [%s] para %s", notification_id, target_url)

    try:
        response = requests.post(target_url, data=body, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("[%s] Falha ao entregar notificação [%s]; será reentregue.", NotificationStatus.RETRYING, notification_id)
        raise

    logger.info(
        "[%s] <<< Notificação [%s] entregue com sucesso (HTTP %s).",
        NotificationStatus.DELIVERED,
        notification_id,
        response.status_code,
    )
