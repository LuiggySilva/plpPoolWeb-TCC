from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField
from .models import Questao, Tag, Periodo, Monitor, Linguagem, Teste, BackupDB
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import django_filters

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
        ]
        labels = {
            'username':'Nome',
            'email':'Email',
        }
        field_classes = {"username": UsernameField}



class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
        ]
        labels = {
            'username':'Nome',
            'email':'Email',
        }



class QuestaoFilter(django_filters.FilterSet):
    enunciado = django_filters.CharFilter(
        label=False, 
        lookup_expr='icontains', 
        widget=forms.widgets.TextInput(attrs={'placeholder': 'Enunciado...'})
    )
    tags = django_filters.MultipleChoiceFilter(
        conjoined=True,
        label=False, 
        choices=(Tag.objects.values_list('pk', 'nome')), 
        widget=forms.widgets.SelectMultiple(
            attrs={'multiple': 'multiple', 'id':'chkveg1'}
        )
    )
    periodo = django_filters.MultipleChoiceFilter(
        label=False, 
        choices=(Periodo.objects.values_list('pk', 'nome')),
        widget=forms.widgets.SelectMultiple(
            attrs={'multiple': 'multiple', 'id':'chkveg2'}
        )
    )
    linguagem = django_filters.MultipleChoiceFilter(
        label=False, 
        choices=(Linguagem.objects.values_list('pk', 'nome')),
        widget=forms.widgets.SelectMultiple(
            attrs={'multiple': 'multiple', 'id':'chkveg3'}
        )
    )
    tipo = django_filters.MultipleChoiceFilter(
        label=False, 
        choices=(Questao.Tipo.choices),
        widget=forms.widgets.SelectMultiple(
            attrs={'multiple': 'multiple', 'id':'chkveg4'}
        )
    )

    class Meta:
        model = Questao
        fields = ['enunciado', 'tags', 'periodo', 'linguagem', 'tipo']



class QuestaoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestaoForm, self).__init__(*args, **kwargs)
        self.fields['linguagem'].empty_label = None

    class Meta:
        model = Questao
        fields = [
            'enunciado',
            'codigo',
            'descricao',
            'tags',
            'tipo',
            'linguagem'
        ]
        labels = {
            'enunciado':"Enunciado",
            'codigo':"Código",
            'descricao':"Descrição",
            'tags':"Tags",
            'linguagem':"Linguagem",
            'tipo':"Tipo"
        }
        widgets = {
            'tags': forms.widgets.SelectMultiple(
                        attrs={'multiple': 'multiple', 'id':'chkveg1'}
                    ),
            'tipo': forms.widgets.Select(),
        }
    


class TesteForm(forms.ModelForm):
    class Meta:
        model = Teste
        exclude = ['questao']
        
TesteFormSet = modelformset_factory(Teste, fields=("entrada", "saida", "tipo"), extra=1)



class PeriodoForm(forms.ModelForm): 
    class Meta:
        model = Periodo
        fields = '__all__'

    def clean(self):
        cd = self.cleaned_data
        p = Periodo.objects.filter(ativo=True)
        if(p.count() == 1 and p[0].nome != cd.get('nome')):
            if (cd.get('ativo')):
                raise ValidationError(
                    _('Outro período já está ativo'),
                )

        if cd.get('monitores'):
            cd.get('monitores').all().update(is_active=cd.get('ativo'))

            Monitor.objects.exclude(
                matricula__in=cd.get('monitores').values_list('matricula')
            ).update(is_active=False)
            
        return cd



class BackupDBForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BackupDBForm, self).__init__(*args, **kwargs)
        self.fields['file'].label = "Escolher arquivo"
    
    class Meta:
        model = BackupDB
        fields = ['file',]
        widgets = {
            "file": forms.FileInput(attrs={
                'accept': ".json", "hidden":"", 'onchange':"setBackupFileNameInBNT(this)"}
            ),
        }
