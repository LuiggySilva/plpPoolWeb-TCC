import logging
import os
import shutil
import tempfile
from enum import StrEnum

import docker
import requests
from urllib3.exceptions import ReadTimeoutError

from django.conf import settings

logger = logging.getLogger(__name__)

DOCKERFILES_DIR = settings.BASE_DIR / "code_compiler" / "dockerfiles"
BASE_DIR = "/tmp/shared_codes"
IN_DOCKER = os.environ.get("PROD_ENVIROMENT") == "1"

os.makedirs(BASE_DIR, exist_ok=True)
temp_dir = tempfile.mkdtemp(dir=BASE_DIR)
folder_name = os.path.basename(temp_dir)


class LanguageExtensions(StrEnum):
    CPP = "cpp"
    PROLOG = "pl"
    HASKELL = "hs"
    C = "c"

    @classmethod
    def get(cls, name):
        match name:
            case "cpp":
                return cls.CPP
            case "prolog":
                return cls.PROLOG
            case "haskell":
                return cls.HASKELL
            case "c":
                return cls.C
            case _:
                return "txt"


class CodeExecutor:
    def __init__(self, debug):
        self.client = None
        self.debug = debug
        self.MEM_LIMIT = "256m"
        self.CPU_QUOTA = 50000  # 50% de um núcleo
        self.TIMEOUT = settings.CODE_EXECUTION_TIMEOUT_SECONDS
        self.logger = logger

        self.LANG_CONFIG = {
            "c": {
                "tag": "compiler-c-cpp",
                "build_path": DOCKERFILES_DIR / "c_cpp",
                "dockerfile": "compiler_c_cpp.Dockerfile",
                "file_ext": LanguageExtensions.C,
                "compile": f"gcc main.{LanguageExtensions.C} -O2 -std=c11 -o solution",
                "run": "./solution",
            },
            "cpp": {
                "tag": "compiler-c-cpp",
                "build_path": DOCKERFILES_DIR / "c_cpp",
                "dockerfile": "compiler_c_cpp.Dockerfile",
                "file_ext": LanguageExtensions.CPP,
                "compile": f"g++ main.{LanguageExtensions.CPP} -O2 -std=c++20 -o solution",
                "run": "./solution",
            },
            "haskell": {
                "tag": "compiler-haskell",
                "build_path": DOCKERFILES_DIR / "haskell",
                "dockerfile": "compiler_haskell.Dockerfile",
                "file_ext": LanguageExtensions.HASKELL,
                "compile": f"ghc -v0 -O2 -fno-diagnostics-show-caret main.{LanguageExtensions.HASKELL} -o solution",
                "run": "./solution",
            },
            "prolog": {
                "tag": "compiler-prolog",
                "build_path": DOCKERFILES_DIR / "prolog",
                "dockerfile": "runtime_prolog.Dockerfile",
                "file_ext": LanguageExtensions.PROLOG,
                "compile": None,
                "run": f"swipl -q -s main.{LanguageExtensions.PROLOG} -t main",
            },
        }
        self._images_prepared = False

    def get_client(self):
        if self.client is None:
            self.client = docker.from_env()
        return self.client

    def ensure_images(self):
        if not self._images_prepared:
            self._prepare_images()
            self._images_prepared = True

    def info(self, message, exc_info=False):
        if self.debug:
            self.logger.info(message, exc_info=exc_info)

    def error(self, message, exc_info=False):
        if self.debug:
            self.logger.error(message, exc_info=exc_info)

    def warning(self, message, exc_info=False):
        if self.debug:
            self.logger.warning(message, exc_info=exc_info)

    def _prepare_images(self):
        """Verifica e constrói as imagens se necessário."""
        for lang, config in self.LANG_CONFIG.items():
            try:
                self.get_client().images.get(config["tag"])
                self.logger.info(f"Imagem {config['tag']} já existe.")
            except docker.errors.ImageNotFound:
                self.logger.info(f"Construindo imagem para {lang}...")
                self.get_client().images.build(
                    path=str(config["build_path"]),
                    dockerfile=config["dockerfile"],
                    tag=config["tag"],
                    rm=True,
                )
                self.logger.info(f"Imagem {config['tag']} construída com sucesso.")

    def execute(self, lang, code, inputs=None):
        if lang not in self.LANG_CONFIG:
            self.error(f"Linguagem não suportada: {lang}")
            return {"error": "Linguagem não suportada"}

        config = self.LANG_CONFIG[lang]

        os.makedirs(BASE_DIR, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=BASE_DIR)
        folder_name = os.path.basename(temp_dir)
        os.chmod(temp_dir, 0o777)

        self.info(f"Iniciando execução ({lang}). Diretério temp: {temp_dir}")

        mount_source = "codigo_volume" if IN_DOCKER else temp_dir

        try:
            self.ensure_images()

            source_file = os.path.join(temp_dir, f"main.{config['file_ext']}")
            with open(source_file, "w") as f:
                f.write(code)
            self.info(f"Código fonte escrito em {source_file}")
            os.chmod(source_file, 0o666)

            input_redir = ""
            if inputs:
                input_file_path = os.path.join(temp_dir, "input.txt")
                with open(input_file_path, "w") as f:
                    content = "\n".join(inputs) if isinstance(inputs, list) else inputs
                    f.write(content)
                input_redir = " < input.txt"
                self.info(
                    f"Arquivo de input criado com {len(inputs) if isinstance(inputs, list) else 1} entradas."
                )
                os.chmod(input_file_path, 0o666)

            if config["compile"]:
                exec_command = f"bash -c '{config['compile']} && {config['run']}{input_redir}'"
            else:
                exec_command = f"bash -c '{config['run']}{input_redir}'"

            container = self.get_client().containers.run(
                image=self.LANG_CONFIG[lang]["tag"],
                command=exec_command,
                volumes={mount_source: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace" if not IN_DOCKER else f"/workspace/{folder_name}",
                mem_limit=self.MEM_LIMIT,
                cpu_quota=self.CPU_QUOTA,
                cpu_period=100000,
                network_disabled=True,
                user="1000:1000",
                detach=True,
                pids_limit=32,
                memswap_limit=self.MEM_LIMIT,
                security_opt=["no-new-privileges:true"],
                read_only=True,
                tmpfs={"/tmp": "size=10m,mode=1777", "/var/tmp": "size=5m"},
            )

            try:
                result = container.wait(timeout=self.TIMEOUT)
                output = container.logs(stdout=True, stderr=False).decode("utf-8")
                error_output = container.logs(stdout=False, stderr=True).decode("utf-8")
                exit_code = result["StatusCode"]

                return {
                    "stdout": output,
                    "stderr": error_output,
                    "exit_code": exit_code,
                    "is_timeout": False,
                    "is_system_error": False,
                }

            except (
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
                ReadTimeoutError,
            ):
                self.warning(f"Timeout atingido ({self.TIMEOUT}s). Matando container.")
                try:
                    container.kill()
                except Exception as e:
                    self.warning(f"Erro ao remover container: {e}")
                return {
                    "is_timeout": True,
                    "is_system_error": False,
                    "stdout": "",
                    "stderr": "Time Limit Exceeded",
                }

        except Exception as e:
            self.warning(f"Erro ao preparar o ambiente de execução: {e}", exc_info=True)
            return {
                "is_system_error": True,
                "error_msg": "Erro ao preparar o ambiente de execução.",
            }

        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    self.warning(f"Erro ao remover container: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.info(f"Limpeza concluída para execução ({lang}). Diretório temp: {temp_dir}")
