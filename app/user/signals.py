from django.db.models.signals import post_migrate, post_save
from django.contrib.auth.models import Group, Permission
from django.dispatch import receiver

from .models import Professor, AssistentStudent, SystemSetting


@receiver(post_migrate)
def create_professor_group(sender, **kwargs):
    group, created = Group.objects.get_or_create(name='Professor')

    if created:
        # TODO adicionar permissões específicas para o grupo Professor
        # list(Group.objects.first().permissions.values_list('codename', flat=True))
        codename_list = [
            'add_period', 
            'change_period', 
            'delete_period', 
            'view_period', 

            'add_assistentstudent', 
            'change_assistentstudent', 
            'delete_assistentstudent', 
            'view_assistentstudent', 

            'add_professor', 
            'change_professor', 
            'delete_professor', 
            'view_professor',

            'add_systemsetting', 
            'change_systemsetting', 
            'delete_systemsetting', 
            'view_systemsetting'
        ]
        permissions = Permission.objects.filter(codename__in=codename_list)
        group.permissions.set(permissions)


@receiver(post_save, sender=Professor)
def add_professor_to_group(sender, instance, created, **kwargs):
    if created:
        group, _ = Group.objects.get_or_create(name='Professor')
        instance.groups.add(group)




@receiver(post_migrate)
def create_assistentstudent_group(sender, **kwargs):
    group, created = Group.objects.get_or_create(name='Monitor')

    if created:
        # TODO adicionar permissões específicas para o grupo Monitor
        # list(Group.objects.first().permissions.values_list('codename', flat=True))
        codename_list = [

        ]
        permissions = Permission.objects.filter(codename__in=codename_list)
        group.permissions.set(permissions)


@receiver(post_save, sender=AssistentStudent)
def add_assistentstudent_to_group(sender, instance, created, **kwargs):
    if created:
        group, _ = Group.objects.get_or_create(name='Monitor')
        instance.groups.add(group)




@receiver(post_save, sender=SystemSetting)
def update_is_active_from_users(sender, instance, created, **kwargs):
    if instance.active_period is None:
        AssistentStudent.objects.filter(role='monitor').update(is_active=False)
    else:
        AssistentStudent.objects.filter(role='monitor', period=instance.active_period).update(is_active=True)
        AssistentStudent.objects.filter(role='monitor').exclude(period=instance.active_period).update(is_active=False)