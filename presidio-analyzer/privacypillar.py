import yaml
import os
from typing import Optional
from flask import request, jsonify
from langdetect import detect, DetectorFactory, LangDetectException
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.analyzer_engine import AnalyzerEngine
from presidio_analyzer.analyzer_request import AnalyzerRequest
# from presidio_analyzer.recognizer_registry import RecognizerRegistry
from presidio_analyzer.recognizer_registry import PrivacyPillarRecognizerRegistry
from app_pp import Server
from sortedcontainers import SortedList
# from .hash_functions import generate_hash
# from proxy import set_proxy_env_vars

DEFAULT_PORT = "3000"
LANG_CONF_FILE = "sample_lang_conf.yaml"

from model_downloader import ModelDownloader


class Lingua:
    """Wrapper for the langdetect library."""

    def __init__(self, supported_languages: list[str]):
        self.supported_languages = supported_languages
        # Set seed for consistent results
        DetectorFactory.seed = 0

    def detect_language_of(self, text: str) -> Optional[str]:
        """Detect the language of the given text."""
        try:
            detected_lang = detect(text)
            # Only return the language if it's in our supported languages
            if detected_lang in self.supported_languages:
                return detected_lang
            return None
        except (LangDetectException, Exception):
            return None


class SynologyServer (Server):
    def __init__(self):
        # set_proxy_env_vars()
        supported_languages, entities, score_threshold = self._get_conf_info()
        self.supported_languages = supported_languages
        self.entities = entities
        self.score_threshold = score_threshold
        self.lingua = Lingua(supported_languages)
        super().__init__()
        self.model_downloader = ModelDownloader(self.logger)

        # this method is deprecated after AIConsole-1.2
        @self.app.route("/anonymize", methods=["POST"])
        def anonymize() -> tuple[str, int]:
            """Execute the anonymizer function."""
            req_data = request.get_json()
            text = req_data.get("text")
            if not text:
                return jsonify(error="No text provided"), 400
            analyzer_results = req_data.get("analyzer_results")
            if analyzer_results is None:
                return jsonify(error="No analyzer results provided"), 400

            # Use non-overlapping entities with the highest score
            analyzer_results = sorted(analyzer_results, key=lambda x: (-x['score'], x['start']))
            filtered_results = SortedList(key=lambda x: x['start'])
            for result in analyzer_results:
                idx = filtered_results.bisect_left(result)
                prevIntersect = False if idx == 0 else filtered_results[idx - 1]['end'] > result['start']
                nextIntersect = False if idx == len(filtered_results) else filtered_results[idx]['start'] < result['end']
                if not prevIntersect and not nextIntersect:
                    filtered_results.add(result)

            entities = []
            deanonymizer_map = dict()
            for result in filtered_results:
                start = result['start']
                end = result['end']
                entity_type = result['entity_type']
                entity = text[start:end]
                # tag = f"{{{entity_type}:{generate_hash(entity)}}}"
                entities.append({
                    "start": start,
                    "end": end,
                    # "tag": tag,
                })
                # deanonymizer_map[tag] = entity

            return jsonify({"entities": entities, "deanonymizer_map": deanonymizer_map}), 200

        @self.app.route("/add_model", methods=["POST"])
        def add_model() -> tuple[str, int]:
            """Download a model for a specific language."""
            model = request.get_json().get("model")
            if not model:
                return jsonify(error="No model provided"), 400
            if self.model_downloader.is_downloading():
                return jsonify(error="Another model is being downloaded"), 503
            try:
                self.model_downloader.download(model)
                return jsonify(success=True), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during "
                    f"ModelDownloader.download(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        @self.app.route("/add_model/cancel", methods=["POST"])
        def cancel_add_model() -> tuple[str, int]:
            """Cancel the model download task."""
            try:
                self.model_downloader.cancel()
                return jsonify(success=True), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during "
                    f"ModelDownloader.cancel(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        @self.app.route("/add_model/status", methods=["GET"])
        def add_model_status() -> tuple[str, int]:
            """Check the status of the model download task."""
            status = "running" if self.model_downloader.is_downloading() else "done"
            return jsonify(status=status), 200

        @self.app.route("/remove_model", methods=["POST"])
        def remove_model() -> tuple[str, int]:
            """Remove a model for a specific language."""
            model = request.get_json().get("model")
            if not model:
                return jsonify(error="No model provided"), 400
            try:
                self.model_downloader.remove(model)
                return jsonify(success=True), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during "
                    f"ModelDownloader.remove(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        @self.app.route("/detect_language", methods=["POST"])
        def detect_language() -> tuple[str, int]:
            """Detect the language of the given text."""
            try:
                text = request.get_json().get("text")
                lang = self.lingua.detect_language_of(text)
                return jsonify(lang), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"LanguageDetector.detect_language_of(). {e}"
                )
                return jsonify(error=e.args[0]), 500

    def get_analyze_request(self, request) -> AnalyzerRequest:
        """Get the analyze data from the request."""
        req_data = AnalyzerRequest(request.get_json())
        # if can't determine language confidently, a default is needed for further processing
        req_data.language = self.lingua.detect_language_of(req_data.text) or self.supported_languages[0]
        req_data.entities = self.entities
        return req_data

    def create_analyzer_engine(self):
        nlp_engine = self._get_nlp_engine()
        registry = PrivacyPillarRecognizerRegistry(
            languages=self.supported_languages,
            nlp_engine=nlp_engine,
            entities=self.entities,
        )
        return AnalyzerEngine(
            default_score_threshold=self.score_threshold,
            supported_languages=self.supported_languages,
            nlp_engine=nlp_engine,
            registry=registry,
        )

    @staticmethod
    def _get_conf_info() -> tuple[list[str], list[str], float]:
        conf_file= os.environ.get("LANG_CONF_FILE", LANG_CONF_FILE)
        print(f"Loading config from {conf_file}")
        with open(conf_file, "r") as f:
            config = yaml.safe_load(f)
        languages = [model["lang_code"] for model in config["models"]]
        entities = [entity for entity in config["entities"]]
        score_threshold = config["score_threshold"] if "score_threshold" in config else 0.85
        return languages, entities, score_threshold

    @staticmethod
    def _get_nlp_engine():
        conf_file = os.environ.get("LANG_CONF_FILE", LANG_CONF_FILE)
        return NlpEngineProvider(conf_file=conf_file).create_engine()

def create_pp_app():  # noqa
    server = SynologyServer()
    return server.app

if __name__ == "__main__":
    # server = SynologyServer()
    # port = int(os.environ.get("PORT", DEFAULT_PORT))
    # server.app.run(host="0.0.0.0", port=port)
    server = create_pp_app()
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    server.run(host="0.0.0.0", port=port)

    
