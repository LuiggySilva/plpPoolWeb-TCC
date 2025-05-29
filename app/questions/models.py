from django.db import models

from .validators import validate_period_format

class Period(models.Model):
    name = models.CharField(
        verbose_name="Nome do Período", 
        max_length=6, 
        unique=True,
        validators=[validate_period_format],
        help_text="Formato: AAAA.S (ex: 2024.1)"    
    )

    class Meta:
        verbose_name = "Período"
        verbose_name_plural = "Períodos"

    def __str__(self):
        return self.name