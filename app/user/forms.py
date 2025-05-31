from django import forms

from .models import Professor, AssistentStudent


class ProfessorCreationForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ('email', 'registration', 'name', 'is_active')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(user.registration)
        if commit:
            user.save()
        return user


class AssistentStudentCreationForm(forms.ModelForm):
    class Meta:
        model = AssistentStudent
        fields = ('email', 'registration', 'name', 'github', 'period', 'is_active')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(user.registration)
        if commit:
            user.save()
        return user
