from django.core.exceptions import ValidationError
import re

def validate_period_format(value):
    # Regex para validar o formato "AAAA.S" (ex: 2024.1)
    match = re.fullmatch(r'(\d{4})\.(\d)', value)
    if not match:
        raise ValidationError("Formato inválido. Use o padrão AAAA.S, como 2024.1")

    year, semester = int(match.group(1)), int(match.group(2))

    if year <= 2010:
        raise ValidationError("O ano deve ser maior que 2010.")

    if semester not in [0, 1, 2]:
        raise ValidationError("O semestre deve ser 0, 1 ou 2.")
