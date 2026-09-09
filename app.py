import logging

from flask import Flask, jsonify

from capabilities.aspectos.routes import aspectos_bp
from capabilities.extrator_atividades.routes import extrator_atividades_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> Flask:
    flask_app = Flask(__name__)
    flask_app.register_blueprint(aspectos_bp)
    flask_app.register_blueprint(extrator_atividades_bp)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy"}), 200

    return flask_app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
