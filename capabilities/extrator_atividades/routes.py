import logging
import os
import tempfile

from flask import Blueprint, jsonify, request
from rq.job import Job

from extensions import extrator_atividades_queue, redis_conn

from . import pipeline
from .tasks import process_extraction

logger = logging.getLogger(__name__)

extrator_atividades_bp = Blueprint("extrator_atividades", __name__)


def _salvar_arquivo_temporario(file) -> str:
    _, ext = os.path.splitext(file.filename)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"upload_{os.urandom(8).hex()}{ext}")
    file.save(temp_path)
    return temp_path


@extrator_atividades_bp.route("/extract", methods=["POST"])
def extract():
    """Contrato síncrono já consumido pelo mymobiconfapi (ExtractService/ScheduleService) — sem mudanças."""
    if "file" not in request.files:
        return jsonify({"detail": "Nenhum arquivo foi enviado."}), 400

    file = request.files["file"]
    temp_path = _salvar_arquivo_temporario(file)

    try:
        resultado = pipeline.run_pipeline(temp_path, file.filename)
        return jsonify(resultado), 200
    except ValueError as ve:
        return jsonify({"detail": str(ve)}), 400
    except Exception as e:
        return jsonify({"detail": f"Erro interno no pipeline de IA: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@extrator_atividades_bp.route("/extract/async", methods=["POST"])
def extract_async():
    """
    Variante assíncrona: enfileira o job na fila `extrator_atividades` e
    responde 202 na hora. Use quando o arquivo for grande o bastante para o
    pipeline (extração + chamada à LLM) ultrapassar o timeout aceitável de uma
    requisição síncrona.

    Campos de form opcionais: `webhook_url` (senão usa DASHBOARD_WEBHOOK_URL)
    e `evento_id` (repassado no payload do webhook, para o dashboard saber
    qual página revalidar). O resultado também pode ser consultado por
    polling em GET /extract/jobs/<job_id>.
    """
    if "file" not in request.files:
        return jsonify({"detail": "Nenhum arquivo foi enviado."}), 400

    file = request.files["file"]
    temp_path = _salvar_arquivo_temporario(file)
    webhook_url = request.form.get("webhook_url")
    evento_id = request.form.get("evento_id")

    job = extrator_atividades_queue.enqueue(
        process_extraction,
        temp_path,
        file.filename,
        webhook_url,
        evento_id,
        job_timeout="10m",
    )

    return jsonify({"job_id": job.id, "status": "PENDING"}), 202


@extrator_atividades_bp.route("/extract/jobs/<job_id>", methods=["GET"])
def extract_job_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return jsonify({"detail": "Job não encontrado."}), 404

    body = {"job_id": job.id, "status": job.get_status()}

    if job.is_finished:
        body["resultado"] = job.result
    elif job.is_failed:
        body["erro"] = str(job.exc_info) if job.exc_info else "Falha desconhecida."

    return jsonify(body), 200
