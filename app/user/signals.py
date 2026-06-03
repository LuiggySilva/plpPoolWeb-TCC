from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AssistentStudent, SystemSetting


@receiver(post_save, sender=SystemSetting)
def update_is_active_from_users(sender, instance, created, **kwargs):
    '''Atualiza o campo is_active (Permissão de Login) dos assistentes de acordo com o período ativo definido no SystemSetting.'''

    if instance.active_period is None:
        AssistentStudent.objects.filter(role=AssistentStudent.Role.ASSISTENT_STUDENT).update(is_active=False)
    else:
        AssistentStudent.objects.filter(role=AssistentStudent.Role.ASSISTENT_STUDENT, period=instance.active_period).update(is_active=True)
        AssistentStudent.objects.filter(role=AssistentStudent.Role.ASSISTENT_STUDENT).exclude(period=instance.active_period).update(is_active=False)