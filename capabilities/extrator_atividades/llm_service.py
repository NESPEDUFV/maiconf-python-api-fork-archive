import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import logging
import json

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY não foi informada.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def get_json_from_text(self, extracted_text: str, prompt_template: str) -> str:
        logger.info("Enviando texto para a LLM com instrução para saída JSON...")

        system_instruction = (
            "Você é um especialista em processamento e estruturação de dados. Sua principal tarefa é converter um texto bruto, que representa a programação de um evento, em um array JSON estruturado e validado, seguindo estritamente o schema fornecido no prompt do usuário. O texto de entrada pode conter ruídos e inconsistências de formatação."
        )

        user_prompt = f"{extracted_text}{prompt_template}"

        generation_config = genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json"
        )

        try:
            response = self.model.generate_content(
                [system_instruction, user_prompt],
                generation_config=generation_config
            )

            json_response_text = response.text

            try:
                json.loads(json_response_text)
                logger.info("JSON recebido e validado com sucesso.")
                return json_response_text
            except json.JSONDecodeError as e:
                logger.error("A API retornou um JSON inválido. Detalhes: %s", e)
                logger.error("Texto recebido: %s", json_response_text)
                return None

        except Exception as e:
            logger.error("Falha ao chamar a API do Gemini. Detalhes: %s", e)
            return None
