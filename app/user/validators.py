from django.core.exceptions import ValidationError

import re


def validate_registration_format(value):
    if not re.fullmatch(r'\d{9}', value):
        raise ValidationError("A matrícula deve conter exatamente 9 dígitos numéricos (ex: 123456789).")
