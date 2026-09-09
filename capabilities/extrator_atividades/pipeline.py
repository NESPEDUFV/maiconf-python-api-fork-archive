import json
import logging
import os

import config
from .extractors import HTMLExtractor, ImageExtractor, PDFExtractor, SpreadsheetExtractor
from .llm_service import GeminiService

logger = logging.getLogger(__name__)

_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt.txt")


def _carregar_prompt() -> str:
    with open(_PROMPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def run_pipeline(input_path: str, original_filename: str) -> dict:
    """
    Orquestra o pipeline de extração: escolhe o extrator pelo tipo de arquivo,
    extrai o texto bruto e pede à LLM para estruturá-lo como atividades.
    Portado do antigo ai_pipeline/main.py (mymobiconfapi), sem mudança de
    comportamento — mesmo contrato de entrada/saída.
    """
    prompt_template = _carregar_prompt()

    _, file_extension = os.path.splitext(original_filename)
    file_extension = file_extension.lower()

    if file_extension in [".png", ".jpg", ".jpeg"]:
        extractor = ImageExtractor(api_key=config.GOOGLE_VISION_API_KEY)
    elif file_extension == ".pdf":
        extractor = PDFExtractor()
    elif file_extension in [".html", ".htm"]:
        extractor = HTMLExtractor()
    elif file_extension in [".xlsx", ".xls", ".ods"]:
        extractor = SpreadsheetExtractor()
    else:
        raise ValueError(f"Formato de arquivo '{file_extension}' não suportado.")

    extracted_text = extractor.extract(input_path)
    if extracted_text is None:
        raise ValueError("Não foi possível extrair texto do arquivo.")

    gemini_service = GeminiService(api_key=config.GEMINI_API_KEY)
    structured_json_str = gemini_service.get_json_from_text(extracted_text, prompt_template)
    if not structured_json_str:
        raise ValueError("Não foi possível obter o JSON da LLM.")

    logger.debug(structured_json_str)
    return json.loads(structured_json_str)
