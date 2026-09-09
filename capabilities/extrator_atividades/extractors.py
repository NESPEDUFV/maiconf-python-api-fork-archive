# extractors.py
import base64
import logging
import requests
import fitz
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import pandas as pd

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> str:
        pass

# ---

class SpreadsheetExtractor(BaseExtractor):
    """
    Extrai dados de arquivos de planilha usando Pandas.
    A biblioteca Pandas gerencia internamente a codificação de arquivos .xlsx e .xls,
    sendo geralmente muito robusta para esses formatos.
    """
    def extract(self, file_path: str) -> str:
        logger.info("Extraindo dados da planilha '%s' com Pandas...", file_path)
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            df.dropna(how='all', inplace=True)

            # Converte colunas de data para string para evitar problemas de formatação
            for col in df.select_dtypes(include=['datetime', 'datetimetz']).columns:
                df[col] = df[col].astype(str)

            texto_json = df.to_json(orient='records', force_ascii=False, indent=2)

            logger.info("Dados da planilha convertidos para texto com sucesso.")
            logger.debug(texto_json)
            return texto_json
        except Exception as e:
            logger.error("Falha ao processar a planilha '%s'. Detalhes: %s", file_path, e)
            return None

# ---

class HTMLExtractor(BaseExtractor):
    """
    Extrai texto de arquivos HTML usando a BeautifulSoup.
    Implementa uma lógica de fallback de codificação para maior robustez.
    """
    def extract(self, file_path: str) -> str:
        logger.info("Extraindo texto do HTML '%s'...", file_path)
        conteudo_html = None
        try:
            # 1. Tenta abrir com UTF-8, o padrão da web.
            with open(file_path, "r", encoding="utf-8") as f:
                conteudo_html = f.read()
        except UnicodeDecodeError:
            # 2. Se falhar, tenta com Latin-1 (compatível com Windows-1252).
            logger.warning("Falha ao decodificar '%s' como UTF-8. Tentando como Latin-1.", file_path)
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    conteudo_html = f.read()
            except Exception as e_inner:
                logger.error("Falha ao ler o arquivo com múltiplas codificações. Detalhes: %s", e_inner)
                return None
        except Exception as e_outer:
            logger.error("Falha ao processar o HTML '%s'. Detalhes: %s", file_path, e_outer)
            return None

        # Se a leitura do arquivo falhou, retorna None
        if conteudo_html is None:
            return None

        soup = BeautifulSoup(conteudo_html, 'lxml')
        texto_extraido = soup.get_text(separator='\n', strip=True)

        logger.info("Texto extraído com sucesso do HTML.")
        return texto_extraido

# ---

class ImageExtractor(BaseExtractor):
    """
    Extrai texto de imagens usando a API do Google Vision.
    O processo já lida corretamente com UTF-8 na comunicação com a API.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"

    def extract(self, file_path: str) -> str:
        logger.info("Extraindo texto da imagem '%s' com Google Vision...", file_path)
        try:
            with open(file_path, "rb") as image_file:
                my_base64_string = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            logger.error("Arquivo de imagem não encontrado em '%s'.", file_path)
            return None

        payload = {
            "requests": [{"image": {"content": my_base64_string}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]
        }
        response = requests.post(self.url, json=payload)

        if response.status_code == 200:
            result = response.json()
            try:
                # A API do Google sempre retorna texto em UTF-8.
                detected_text = result['responses'][0]['textAnnotations'][0]['description']
                logger.info("Texto extraído da imagem com sucesso.")
                return detected_text
            except (KeyError, IndexError):
                logger.warning("Nenhum texto foi detectado na imagem.")
                return ""
        else:
            logger.error("A requisição para a Vision API falhou com o status %s", response.status_code)
            logger.error("Resposta da API: %s", response.text)
            return None

# ---

class PDFExtractor(BaseExtractor):
    """
    Extrai texto de arquivos PDF usando PyMuPDF (fitz).
    A biblioteca gerencia as complexidades da codificação interna dos PDFs.
    """
    def extract(self, file_path: str) -> str:
        logger.info("Extraindo texto do PDF '%s' com PyMuPDF (fitz)...", file_path)
        full_text = ""
        try:
            with fitz.open(file_path) as doc:
                logger.info("O documento tem %d páginas.", len(doc))
                for i, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text:
                        full_text += page_text + "\n\n--- PRÓXIMA PÁGINA ---\n\n"
            logger.info("Texto extraído do PDF com sucesso.")
            return full_text
        except Exception as e:
            logger.error("Falha ao processar o PDF '%s'. Detalhes: %s", file_path, e)
            return None
