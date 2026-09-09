import logging

from flask import Blueprint, jsonify, request

from .nlp_pipeline import AspectExtractionPipeline

logger = logging.getLogger(__name__)

aspectos_bp = Blueprint("aspectos", __name__)

# Carregados uma única vez, na inicialização do processo — mesmo comportamento
# de antes. É por isso que a API continua rodando com 1 worker (ver Dockerfile):
# duplicar este carregamento por worker estouraria a memória do container.
logger.info("Inicializando pipeline de aspectos (spaCy + SentenceTransformer + pysentimiento)...")
pipeline = AspectExtractionPipeline(distance_threshold=0.3)
logger.info("Pipeline de aspectos pronto.")


@aspectos_bp.route("/analyze", methods=["POST"])
def analyze_comments():
    data = request.get_json()

    if not data or "comments" not in data:
        return jsonify({"error": "Formato inválido. O JSON deve conter a chave 'comments' com uma lista de objetos."}), 400

    comments = data["comments"]

    try:
        resultados = pipeline.processar(comments)
        return jsonify({"status": "success", "data": resultados}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aspectos_bp.route("/analyze/summary", methods=["POST"])
def analyze_comments_summary():
    data = request.get_json()

    if not data or "comments" not in data:
        return jsonify({"error": "Formato inválido. O JSON deve conter a chave 'comments' com uma lista de objetos."}), 400

    comments = data["comments"]

    try:
        resultados = pipeline.processar(comments)

        # Agrupar aspectos
        aspectos_dict = {}
        for r in resultados:
            asp = r.get("aspecto")
            score = r.get("sentimento_score", 0.0)
            if asp:
                if asp not in aspectos_dict:
                    aspectos_dict[asp] = {"mencoes": 0, "total_score": 0.0}
                aspectos_dict[asp]["mencoes"] += 1
                aspectos_dict[asp]["total_score"] += score

        # Formatar a resposta
        resumo = []
        for asp, stats in aspectos_dict.items():
            sentimento_medio = stats["total_score"] / stats["mencoes"] if stats["mencoes"] > 0 else 0.0
            resumo.append({
                "aspecto": asp,
                "mencoes": stats["mencoes"],
                "sentimento_medio": round(sentimento_medio, 3),
            })

        # Ordenar por menções de forma decrescente
        resumo.sort(key=lambda x: x["mencoes"], reverse=True)

        return jsonify({"status": "success", "data": resumo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
