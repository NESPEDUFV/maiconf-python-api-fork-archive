class NotificationStatus:
    """
    Vocabulário de status usado nos logs de entrega de webhook — mesmos nomes
    do NotificationStatus (enum) do maiconfpayment. Aqui o estado real é o do
    job na fila `notifications_egress` (RQ); estes valores documentam a que
    cada fase corresponde e são usados nas mensagens de log.
    """

    PENDING = "PENDING"
    RETRYING = "RETRYING"
    DELIVERED = "DELIVERED"
    DEAD = "DEAD"
