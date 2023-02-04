
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .models import Atividade, Periodo
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

def task():
    date_now = datetime.now()
    semana_antes = date_now + timedelta(days=7)
    atividades = Atividade.objects.filter(periodo__ativo=True)

    for atividade in atividades:
        if(atividade.data.day == date_now.day and 
           atividade.data.month == date_now.month and
           atividade.data.year == date_now.year):
            mail_subject = 'plpPoolWeb: Entrega da atividade até hoje'
            to_email = [email[0] for email in list(Periodo.objects.get(id=atividade.periodo.id).monitores.all().values_list('email'))]
            message = render_to_string(
                'plpPool/email_atividade.html', 
                context={
                    'atividade': atividade
                }
            )
            email = EmailMessage(mail_subject, message, to=to_email)
            email.content_subtype = "html"
            email.send()
        elif (atividade.data.day == semana_antes.day and 
            atividade.data.month == semana_antes.month and
            atividade.data.year == semana_antes.year):
            mail_subject = 'plpPoolWeb: Uma semana para entrega da atividade'
            to_email = [email[0] for email in list(Periodo.objects.get(id=atividade.periodo.id).monitores.all().values_list('email'))]
            message = render_to_string(
                'plpPool/email_atividade.html', 
                context={
                    'atividade': atividade
                }
            )
            email = EmailMessage(mail_subject, message, to=to_email)
            email.content_subtype = "html"
            email.send()


def start():
    scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
    #Todo dia as 05hrs da manhã
    scheduler.add_job(task, 'cron', hour=5, max_instances=1, replace_existing=True)
    scheduler.start()
    
