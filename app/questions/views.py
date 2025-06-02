from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.messages import constants
from django.utils.translation import gettext_lazy as _

from django_filters.views import FilterView

from .forms import QuestionFilter
from .models import Question, Period, Tag, Test


class QuestionListView(LoginRequiredMixin, ListView):
    model = Question
    template_name = "questions/questions.html"
    context_object_name = "questions"
    paginate_by = 10

    def get_queryset(self):
        self.filterset = QuestionFilter(self.request.GET, queryset=Question.objects.all().order_by("-created_at"))
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['current_tab'] = "list"
        return context
    

class AssistentStudentQuestionListView(LoginRequiredMixin, TemplateView):
    template_name = "questions/assistentstudent_questions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = Question.objects.filter(author=self.request.user).order_by("-created_at")
        context['current_tab'] = "assistentstudent_list"
        return context



class QuestionDetailView(LoginRequiredMixin, DetailView):
    model = Question
    template_name = "questions/question.html"
    context_object_name = "question"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['public_tests'] = self.object.tests.filter(type=Test.TestType.PUBLIC)
        context['private_tests'] = self.object.tests.filter(type=Test.TestType.PRIVATE)
        context['current_tab'] = "assistentstudent_list"
        return context