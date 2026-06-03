import re

from django.core.exceptions import ValidationError

MAX_CODE_SIZE = 100 * 1024  # 100KB
MAX_INPUT_SIZE = 50 * 1024  # 50KB
FORBIDDEN_MAP = {
    "c": {
        r"\bsystem\s*\(": 'chamada de sistema "system()"',
        r"\bfork\s*\(": 'criação de processo "fork()"',
        r"\bexec[lvep]*\s*\(": 'execução de binários "exec"',
    },
    "cpp": {
        r"\bsystem\s*\(": 'chamada de sistema "system()"',
        r"\bfork\s*\(": 'criação de processo "fork()"',
        r"\bexec[lvep]*\s*\(": 'execução de binários "exec"',
    },
    "haskell": {
        r"System\.Process": 'módulo de processos "System.Process"',
        r"System\.Cmd": 'módulo de comandos "System.Cmd"',
        r"unsafePerformIO": 'função insegura "unsafePerformIO"',
    },
    "prolog": {
        r"\bshell\s*\(": 'acesso ao shell via "shell()"',
        r"\bsystem\s*\(": 'chamada de sistema "system()"',
        r"\bopen\s*\(": 'abertura de arquivos "open()"',
    },
}


def validate_period_format(value):
    """ Valida o formato do período no padrão AAAA.S, onde S é o semestre (0, 1 ou 2). """
    match = re.fullmatch(r"(\d{4})\.(\d)", value)
    if not match:
        raise ValidationError("Use o padrão AAAA.S, como 2024.1")

    year, semester = int(match.group(1)), int(match.group(2))

    if year <= 2010:
        raise ValidationError("O ano deve ser maior que 2010.")

    if semester not in [0, 1, 2]:
        raise ValidationError("O semestre deve ser 0, 1 ou 2.")


def sanitize_source_code(code, language, max_size=102400):
    """ Sanitiza o código-fonte removendo caracteres nulos e validando tamanho e termos proibidos. """
    if not code:
        raise ValidationError("O código-fonte não pode estar vazio.")

    if len(code) > max_size:
        raise ValidationError(f"O código excede o limite de {max_size // 1024}KB.")

    code = code.replace("\x00", "")

    if language in FORBIDDEN_MAP:
        for pattern, friendly_name in FORBIDDEN_MAP[language].items():
            if re.search(pattern, code):
                raise ValidationError(
                    f"Código bloqueado por segurança: O uso de {friendly_name} não é permitido nesta plataforma."
                )

    return code


def sanitize_program_input(input_data, max_size=MAX_INPUT_SIZE):
    """Sanitiza casos de teste e entradas manuais preservando a estrutura."""

    if input_data is None:
        return ""
    if len(input_data) > max_size:
        raise ValidationError(f"A entrada excede o limite de {max_size // 1024}KB.")

    return input_data
