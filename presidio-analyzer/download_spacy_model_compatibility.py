import json

from spacy.cli.download import get_compatibility


MODEL_COMP_JSON = "spacy_model_compatibility.json"


if __name__ == "__main__":
    # { "model_name": [ "latest_version", "older_version", ... ] }
    comp = get_compatibility()
    with open(MODEL_COMP_JSON, "w") as f:
        json.dump(comp, f)
