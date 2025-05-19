from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Survey, Question, Choice, Response, UserProfile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio',)

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ('title', 'description', 'is_public', 'password', 'end_date', 'is_anonymous', 'max_responses', 'template')
        widgets = {
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('text', 'question_type', 'required', 'order', 'conditional_question', 'conditional_value')
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'conditional_question': forms.Select(attrs={'class': 'form-control'}),
            'conditional_value': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ('text', 'order')
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ('text_response', 'choice_response', 'scale_response')
        widgets = {
            'text_response': forms.Textarea(attrs={'class': 'form-control'}),
            'scale_response': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        }

    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question', None)
        super().__init__(*args, **kwargs)

        if question:
            if question.question_type == 'single_choice':
                self.fields['choice_response'] = forms.ModelChoiceField(
                    queryset=question.choices.all(),
                    widget=forms.RadioSelect,
                    required=question.required,
                    empty_label=None
                )
                self.fields['text_response'].widget = forms.HiddenInput()
                self.fields['scale_response'].widget = forms.HiddenInput()
            elif question.question_type == 'multiple_choice':
                self.fields['choice_response'] = forms.ModelMultipleChoiceField(
                    queryset=question.choices.all(),
                    widget=forms.CheckboxSelectMultiple,
                    required=question.required,
                )
                self.fields['text_response'].widget = forms.HiddenInput()
                self.fields['scale_response'].widget = forms.HiddenInput()
            elif question.question_type == 'scale':
                self.fields['scale_response'].widget = forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10})
                self.fields['text_response'].widget = forms.HiddenInput()
                if 'choice_response' in self.fields:
                    del self.fields['choice_response']
            else:  # text
                self.fields['text_response'].widget = forms.Textarea(attrs={'class': 'form-control'})
                if 'choice_response' in self.fields:
                    del self.fields['choice_response']
                if 'scale_response' in self.fields:
                    del self.fields['scale_response']