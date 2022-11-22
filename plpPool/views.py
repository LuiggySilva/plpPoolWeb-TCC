from django.shortcuts import redirect, reverse, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView, 
    ListView, 
    DetailView, 
    DeleteView, 
    UpdateView, 
    CreateView, 
    FormView, 
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import Questao, Tag, Periodo, Atividade, Monitor, Teste
from .forms import QuestaoFilter, QuestaoForm, TesteFormSet, TesteForm
from django.forms import modelformset_factory
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from django.http import HttpResponseRedirect

# Create your views here.

def teste(request):
    q = Questao.objects.all()
    return render(request, 'plpPool/test.html', {"q":q})

@login_required
def todas_questoes(request): 
    f = QuestaoFilter(request.GET, queryset=Questao.objects.all())
    return render(request, 'plpPool/todas_questoes.html', {'questao_filter': f})

@login_required
def questao(request, pk):
    q = Questao.objects.get(id=pk)
    return render(request, 'plpPool/questao.html', {'questao': q})

@login_required
def monitor(request):
    periodo_ativo = Periodo.objects.get(ativo=True)
    atividades = Atividade.objects.filter(periodo=periodo_ativo)
    questoes = Questao.objects.filter(periodo=periodo_ativo, autor=request.user)

    return render(
        request,  
        'plpPool/monitor_questoes.html', 
        {
            'form': QuestaoForm,
            'formset': TesteFormSet,
            'atividades': atividades,
            'questoes': questoes
        }
    )

def feedback(request):
    q = Questao.objects.get(id=request.POST.get('pk'))
    message = render_to_string(
        'plpPool/email_feedback.html', 
        context={
            'feedback':request.POST.get('feedback'),
            'questao':q
        }
    )
    mail_subject = f'plpPoolWeb - Feedback - {q}'
    to_email = q.autor.email
    to_prof = request.user.email
    email = EmailMessage(mail_subject, message, to=[to_email, to_prof])
    email.send()
    return redirect(reverse("admin:plpPool_questao_change", args=[request.POST.get('pk')]))

def remover_questao_monitor(request, pk):
    q = get_object_or_404(Questao, pk=pk)
    q.delete()
    return redirect(reverse_lazy("plpPool:monitor_questoes"))

def editar_questao_monitor(request, pk):
    context ={}
 
    q = get_object_or_404(Questao, pk=pk)

    if (request.user != q.autor):
        redirect(reverse_lazy("plpPool:monitor_questoes"))

    form = QuestaoForm(request.POST or None, instance=q)

    TesteFormSetUpdate = modelformset_factory(Teste, form=TesteForm, extra=0, can_delete=True)
    formset = TesteFormSetUpdate(data=request.POST or None, files=request.FILES or None, queryset=Teste.objects.filter(questao__pk=pk))

    if form.is_valid() and formset.is_valid():
        form.save()
        for fs in formset:
            fss = fs.save(commit=False)
            if (fss.id == None):
                t = Teste(
                    tipo=fs.cleaned_data['tipo'], 
                    questao=q, 
                    entrada=fs.cleaned_data['entrada'], 
                    saida=fs.cleaned_data['saida']
                )
                t.save()
            elif (fs.cleaned_data['DELETE'] == True):
                fs = fs.save(commit=False)
                fs.delete()
            else:
                fss.save()
        return redirect(reverse_lazy("plpPool:monitor_questoes"))
 
    context["form"] = form
    context["formset"] = formset
    return render(request, 'plpPool/modificar_questao.html', context)

class MonitorView(TemplateView):
    template_name = "plpPool/monitor_questoes.html"

    def get(self, *args, **kwargs):
        periodo_ativo = Periodo.objects.get(ativo=True)
        atividades = Atividade.objects.filter(periodo=periodo_ativo).order_by('data')
        questoes = Questao.objects.filter(periodo=periodo_ativo, autor=self.request.user)
        formset = TesteFormSet(queryset=Teste.objects.none())

        progresso =  Atividade.objects.filter(periodo=periodo_ativo, linguagem__isnull=False).values_list('linguagem__nome', 'qtd_basicas', 'qtd_avancadas')
        progresso = [list(l) for l in list(progresso)]
        for l in progresso:
            l.extend([0,0,[],[]])

        for index, p in enumerate(progresso):
            for questao in questoes:
                if (questao.linguagem.nome == p[0]):
                    if (questao.tipo == "Básica"):
                        p[3] = p[3]+1
                        p[5].append(questao)
                    else:
                        p[4] = p[4]+1
                        p[6].append(questao)
                    progresso[index] = p

        return self.render_to_response({
            'form': QuestaoForm,
            'formset': formset,
            'atividades': atividades,
            'questoes': questoes,
            'progresso': progresso
        })

    def post(self, *args, **kwargs):
        periodo_ativo = Periodo.objects.get(ativo=True)
        atividades = Atividade.objects.filter(periodo=periodo_ativo)
        questoes = Questao.objects.filter(periodo=periodo_ativo, autor=self.request.user)
        autor = Monitor.objects.get(email=self.request.user.email) 
        form = QuestaoForm(data=self.request.POST)
        
        tags_id = [] 
        for t in form['tags']:
            if t.data['selected']:
                tags_id.append(t.data['value'].value)

        formset = TesteFormSet(data=self.request.POST)

        if formset.is_valid() and form.is_valid():
            f = form.save(commit=False)
            f.periodo = periodo_ativo
            f.autor = autor
            f.save() 
            f.tags.set(Tag.objects.filter(id__in=tags_id))
            f.save() 
            for fs in formset:
                fs = fs.save(commit=False)
                fs.questao = f
                fs.save() 
            return redirect(reverse_lazy("plpPool:monitor_questoes"))

        return self.render_to_response({
            'form': QuestaoForm,
            'formset': formset,
            'atividades': atividades,
            'questoes': questoes
        })
