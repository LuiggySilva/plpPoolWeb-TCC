from django.shortcuts import redirect, reverse, render
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
from .forms import QuestaoFilter, QuestaoForm, TesteFormSet

# Create your views here.

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



class MonitorView(TemplateView):
    template_name = "plpPool/monitor_questoes.html"

    def get(self, *args, **kwargs):
        periodo_ativo = Periodo.objects.get(ativo=True)
        atividades = Atividade.objects.filter(periodo=periodo_ativo)
        questoes = Questao.objects.filter(periodo=periodo_ativo, autor=self.request.user)
        formset = TesteFormSet(queryset=Teste.objects.none())
        return self.render_to_response({
            'form': QuestaoForm,
            'formset': formset,
            'atividades': atividades,
            'questoes': questoes
        })

    # Define method to handle POST request
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
            return redirect(reverse_lazy("plpPool:pagina_inicial"))

        return self.render_to_response({
            'form': QuestaoForm,
            'formset': formset,
            'atividades': atividades,
            'questoes': questoes
        })
