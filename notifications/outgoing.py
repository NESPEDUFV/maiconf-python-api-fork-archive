import logging
import uuid

from rq import Retry

import config
from extensions import notifications_egress_queue
from notifications.status import NotificationStatus

logger = logging.getLogger(__name__)


def enqueue_delivery(target_url: str, event_type: str, payload: dict) -> str:
    """
    Enfileira a entrega assinada de um webhook na fila `notifications_egress`
    (mesmo nome e mesma política de retry — 3 tentativas, backoff exponencial
    a partir de IA_WEBHOOK_RETRY_DELAY_MS — usadas pelo maiconfpayment).
    """
    notification_id = str(uuid.uuid4())
    body = {
        "event_id": notification_id,
        "event_type": event_type,
        **payload,
    }

    base_delay_s = max(int(config.egress_retry_delay_ms() / 1000), 1)
    retry = Retry(max=3, interval=[base_delay_s, base_delay_s * 2, base_delay_s * 4])

    notifications_egress_queue.enqueue(
        "notifications.tasks.deliver_webhook",
        target_url,
        body,
        notification_id,
        retry=retry,
        job_id=notification_id,
    )

    logger.info(
        "[%s] Notificação [%s] (%s) enfileirada para %s.",
        NotificationStatus.PENDING,
        notification_id,
        event_type,
        target_url,
    )
    return notification_id
