from collections import defaultdict
import json
from logging import Logger
import os
from pathlib import Path
import shutil
import sys
import psutil
import multiprocessing

from spacy.cli.download import (
    download as spacy_download,
    get_version as get_latest_spacy_model_version,
)

from download_spacy_model_compatibility import MODEL_COMP_JSON


class ModelDependencyManager:
    def __init__(self, logger: Logger):
        self._logger = logger

        virtual_env_path = os.environ.get("VIRTUAL_ENV", "")
        self._venv_site_packages_dir: Path = Path([x for x in sys.path if x.startswith(virtual_env_path)][0])
        self._original_site_packages: set[str] = self._get_venv_site_packages()
        pythonpath = os.environ.get("PYTHONPATH", "")
        self._local_site_packages_dir: Path = Path(pythonpath)
        self._local_site_packages_dir.mkdir(exist_ok=True)
        self._model_dependencies_path: Path = self._local_site_packages_dir / "model_dependencies.json"

        self._model_dependencies: dict[str, list[str]] = self._load_model_dependencies()
        self._package_references: defaultdict[str, int] = self._get_package_references()

    @property
    def models(self) -> list[str]:
        return list(self._model_dependencies.keys())

    def handle_model_download_complete(self, model: str):
        new_packages = self._get_venv_site_packages() - self._original_site_packages
        self._model_dependencies[model] = list(new_packages)
        for package in new_packages:
            self._package_references[package] += 1
            source_path = self._venv_site_packages_dir / package
            target_path = self._local_site_packages_dir / package
            if target_path.exists():
                shutil.rmtree(source_path)
            else:
                shutil.move(source_path, target_path)
        self._save_model_dependencies()

    def handle_model_download_cancel(self):
        new_packages = self._get_venv_site_packages() - self._original_site_packages
        for package in new_packages:
            path = self._venv_site_packages_dir / package
            shutil.rmtree(path) if path.is_dir() else os.remove(path)

    def handle_model_remove(self, model_name: str):
        for package in self._model_dependencies[model_name]:
            self._package_references[package] -= 1
            if self._package_references[package] == 0:
                path = self._local_site_packages_dir / package
                shutil.rmtree(path) if path.is_dir() else os.remove(path)
        del self._model_dependencies[model_name]
        self._save_model_dependencies()

    def _load_model_dependencies(self) -> dict[str, list[str]]:
        if not self._model_dependencies_path.exists():
            return {}
        with open(self._model_dependencies_path, "r") as f:
            return json.load(f)

    def _save_model_dependencies(self):
        with open(self._model_dependencies_path, "w+") as f:
            json.dump(self._model_dependencies, f)

    def _get_package_references(self) -> defaultdict[str, int]:
        package_references = defaultdict(int)
        for packages in self._model_dependencies.values():
            for package in packages:
                package_references[package] += 1
        return package_references

    def _get_venv_site_packages(self) -> set[str]:
        return {x.name for x in self._venv_site_packages_dir.iterdir()}


class ModelDownloader:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.dependency_manager: ModelDependencyManager = ModelDependencyManager(logger)
        self.download_process = None

        with open(MODEL_COMP_JSON, "r") as f:
            self.model_version_map: dict = json.load(f)

    def download(self, model: str):
        """Download the model."""
        if model in self.dependency_manager.models:
            return

        if self.is_downloading():
            raise Exception("Another model is being downloaded")

        self.download_process = multiprocessing.Process(target=self._download, args=(model,))
        self.download_process.start()

    def is_downloading(self):
        """Check if a model is being downloaded."""
        return self.download_process is not None and self.download_process.is_alive()

    def _download(self, model: str):
        """Download the model."""
        latest_version = get_latest_spacy_model_version(model, self.model_version_map)
        full_model_name = f"{model}-{latest_version}"
        spacy_download(full_model_name, direct=True)
        self.dependency_manager.handle_model_download_complete(model)

    def cancel(self):
        """Cancel the model download."""
        if not self.is_downloading():
            return

        children = psutil.Process(self.download_process.pid).children(recursive=True)
        for child in children:
            child.terminate()
        psutil.wait_procs(children)

        self.download_process.terminate()
        self.download_process = None

        self.dependency_manager.handle_model_download_cancel()

    def remove(self, model: str):
        """Remove the model."""
        if model in self.dependency_manager.models:
            self.dependency_manager.handle_model_remove(model)
