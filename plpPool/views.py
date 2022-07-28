from django.shortcuts import redirect, reverse,render
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
from .models import Questao, Tag, Periodo
from .forms import QuestaoFilter, QuestaoForm

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
    return render(request, 'plpPool/monitor_questoes.html', {'form': QuestaoForm})
