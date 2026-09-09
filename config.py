import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")

# Mesmas variáveis usadas pelo BullModule do mymobiconfapi (src/app.module.ts):
# reutiliza o Redis que já existe — mmc-redis em dev, ElastiCache em prod —
# em vez de subir uma instância própria. TLS segue o mesmo flag SSL usado em
# todo o resto do projeto (rejectUnauthorized desligado, igual ao lado Node).
AWS_REDIS_HOST = os.getenv("AWS_REDIS_HOST", "mmc-redis")
AWS_REDIS_PORT = os.getenv("AWS_REDIS_PORT", "6379")
SSL_ENABLED = os.getenv("SSL", "false").lower() == "true"

# URL do handler de webhook no mymobiconfdashboard. Usado como destino padrão
# quando POST /extract/async não recebe um `webhook_url` explícito no form.
DASHBOARD_WEBHOOK_URL = os.getenv("DASHBOARD_WEBHOOK_URL")

# Segredo compartilhado para assinar (HMAC-SHA256, header x-webhook-signature)
# as notificações enviadas ao dashboard — mesmo padrão do PAYMENT_WEBHOOK_SECRET
# usado pelo maiconfpayment para notificar o mymobiconfapi.
IA_WEBHOOK_SECRET = os.getenv("IA_WEBHOOK_SECRET")

DEFAULT_EGRESS_RETRY_DELAY_MS = 15 * 60 * 1000


def egress_retry_delay_ms() -> int:
    """
    Delay base (ms) do backoff exponencial de reentrega de webhooks — mesmo
    papel do EGRESS_RETRY_DELAY_MS do maiconfpayment (fila notifications_egress).
    """
    raw = os.getenv("IA_WEBHOOK_RETRY_DELAY_MS")
    try:
        value = int(raw)
        return value if value >= 0 else DEFAULT_EGRESS_RETRY_DELAY_MS
    except (TypeError, ValueError):
        return DEFAULT_EGRESS_RETRY_DELAY_MS
