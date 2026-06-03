import re

from django.core.exceptions import ValidationError


def validate_registration_format(value):
    """Valida se a matrícula tem exatamente 9 dígitos numéricos (ex: 123456789)."""
    if not re.fullmatch(r"\d{9}", value):
        raise ValidationError(
            "A matrícula deve conter exatamente 9 dígitos numéricos (ex: 123456789)."
        )
