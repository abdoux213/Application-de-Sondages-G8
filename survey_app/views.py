from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count
import csv
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from .models import Survey, Question, Choice, Response, UserProfile, SurveyShare, SurveyNotification
from .forms import (
    UserRegistrationForm, UserProfileForm, SurveyForm, QuestionForm,
    ChoiceForm, ResponseForm
)

def home(request):
    surveys = Survey.objects.filter(is_public=True)
    if request.user.is_authenticated:
        user_surveys = Survey.objects.filter(creator=request.user)
        return render(request, 'survey_app/home.html', {
            'surveys': surveys,
            'user_surveys': user_surveys
        })
    return render(request, 'survey_app/home.html', {'surveys': surveys})

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'survey_app/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte créé avec succès!')
            return redirect('home')
        return render(request, 'survey_app/register.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    def get(self, request):
        profile = request.user.userprofile
        form = UserProfileForm(instance=profile)
        surveys = Survey.objects.filter(creator=request.user)
        return render(request, 'survey_app/profile.html', {
            'form': form,
            'surveys': surveys
        })

    def post(self, request):
        profile = request.user.userprofile
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('survey_app:profile')
        return render(request, 'survey_app/profile.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class SurveyCreateView(View):
    def get(self, request):
        # Check if the user is 'abdo'
        if request.user.username != 'abdo':
            messages.error(request, 'Seul l\'utilisateur abdo est autorisé à créer des sondages.')
            return redirect('survey_app:home')

        form = SurveyForm()
        return render(request, 'survey_app/survey_create.html', {'form': form})

    def post(self, request):
        # Check if the user is 'abdo'
        if request.user.username != 'abdo':
            messages.error(request, 'Seul l\'utilisateur abdo est autorisé à créer des sondages.')
            return redirect('survey_app:home')

        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.save()
            messages.success(request, 'Sondage créé avec succès!')
            return redirect('survey_app:survey_detail', survey_id=survey.id)
        return render(request, 'survey_app/survey_create.html', {'form': form})

class SurveyDetailView(View):
    def get(self, request, survey_id):
        survey = get_object_or_404(Survey, pk=survey_id)
        if not survey.is_public and request.user != survey.creator:
            messages.error(request, 'Vous n\'avez pas accès à ce sondage.')
            return redirect('home')
        
        questions = Question.objects.filter(survey=survey)
        return render(request, 'survey_app/survey_detail.html', {
            'survey': survey,
            'questions': questions
        })

@method_decorator(login_required, name='dispatch')
class AddQuestionView(View):
    def get(self, request, survey_id):
        # Check if the user is 'abdo'
        if request.user.username != 'abdo':
            messages.error(request, 'Seul l\'utilisateur abdo est autorisé à ajouter des questions.')
            return redirect('survey_app:home')

        survey = get_object_or_404(Survey, pk=survey_id)
        # The creator check might still be useful if 'abdo' can create surveys but not edit others'
        if request.user != survey.creator:
             messages.error(request, 'Vous n\'avez pas la permission d\'ajouter des questions à ce sondage.')
             return redirect('survey_app:home')

        form = QuestionForm()
        questions = Question.objects.filter(survey=survey)
        return render(request, 'survey_app/add_question.html', {
            'form': form,
            'survey': survey,
            'questions': questions
        })

    def post(self, request, survey_id):
        # Check if the user is 'abdo'
        if request.user.username != 'abdo':
            messages.error(request, 'Seul l\'utilisateur abdo est autorisé à ajouter des questions.')
            return redirect('survey_app:home')

        survey = get_object_or_404(Survey, pk=survey_id)
         # The creator check might still be useful
        if request.user != survey.creator:
             messages.error(request, 'Vous n\'avez pas la permission d\'ajouter des questions à ce sondage.')
             return redirect('survey_app:home')

        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = survey
            question.save()

            if question.question_type in ['single_choice', 'multiple_choice']:
                choices = request.POST.getlist('choices')
                for i, choice_text in enumerate(choices):
                    if choice_text.strip():
                        Choice.objects.create(
                            question=question,
                            text=choice_text.strip(),
                            order=i
                        )

            messages.success(request, 'Question ajoutée avec succès!')
            return redirect('survey_app:survey_detail', survey_id=survey.id)

        questions = Question.objects.filter(survey=survey)
        return render(request, 'survey_app/add_question.html', {
            'form': form,
            'survey': survey,
            'questions': questions
        })

@method_decorator(login_required, name='dispatch')
class TakeSurveyView(View):
    def get(self, request, survey_id):
        survey = get_object_or_404(Survey, pk=survey_id)
        if not survey.is_public and request.user != survey.creator:
            messages.error(request, 'Vous n\'avez pas accès à ce sondage.')
            return redirect('home')
        
        if survey.end_date and survey.end_date < timezone.now():
            messages.error(request, 'Ce sondage est terminé.')
            return redirect('home')
        
        if survey.max_responses > 0:
            response_count = Response.objects.filter(survey=survey).count()
            if response_count >= survey.max_responses:
                messages.error(request, 'Ce sondage a atteint sa limite de réponses.')
                return redirect('home')
        
        questions = Question.objects.filter(survey=survey)
        question_forms = [(question, ResponseForm(question=question)) for question in questions]
        return render(request, 'survey_app/take_survey.html', {
            'survey': survey,
            'question_forms': question_forms
        })

    def post(self, request, survey_id):
        print("Debug: request.POST data:", request.POST) # Debug print for POST data
        survey = get_object_or_404(Survey, pk=survey_id)
        if not survey.is_public and request.user != survey.creator:
            messages.error(request, 'Vous n\'avez pas accès à ce sondage.')
            return redirect('home')
        
        questions = Question.objects.filter(survey=survey)
        forms = []
        all_valid = True

        for question in questions:
            form = ResponseForm(request.POST, question=question, prefix=str(question.id))

            # Debug: Print raw POST data for choice_response for this specific question before workaround
            if question.question_type in ['single_choice', 'multiple_choice']:
                field_name_prefixed = f"{question.id}-choice_response"
                print(f"Debug: Raw POST data for {field_name_prefixed} BEFORE workaround: {request.POST.getlist(field_name_prefixed)}")

            # --- Start of Debugging/Workaround Block ---
            # Check if choice_response data is missing from the prefixed name but present without prefix
            field_name_unprefixed = "choice_response"

            if question.question_type in ['single_choice', 'multiple_choice']:
                if not request.POST.getlist(field_name_prefixed) and request.POST.getlist(field_name_unprefixed):
                    # If data is found without prefix, manually add it to the form's data dictionary
                    # before is_valid() is called. We need a mutable copy of request.POST.
                    if not hasattr(request.POST, '_mutable') or not request.POST._mutable:
                         request.POST._mutable = True

                    request.POST.setlist(field_name_prefixed, request.POST.getlist(field_name_unprefixed))
                    print(f"Debug: Assigned unprefixed {field_name_unprefixed} data to prefixed {field_name_prefixed}")
                    # Optionally remove the unprefixed data to avoid confusion, though not strictly necessary for form validation
                    # del request.POST[field_name_unprefixed]

            # --- End of Debugging/Workaround Block ---

            # Debug: Print form data and bound status before is_valid()
            print(f"Debug: Form for question {question.id} is bound: {form.is_bound}")
            print(f"Debug: Form data for question {question.id}: {form.data}")
            if question.question_type in ['single_choice', 'multiple_choice']:
                 field_name_in_form_data = f"{question.id}-choice_response"
                 print(f"Debug: Data in form.data for {field_name_in_form_data}: {form.data.getlist(field_name_in_form_data)}")

            if form.is_valid():
                response = form.save(commit=False)
                response.survey = survey
                response.question = question
                if not survey.is_anonymous and request.user.is_authenticated:
                    response.user = request.user
                response.ip_address = request.META.get('REMOTE_ADDR')
                response.save() # Save the response object to get an ID

                # Sauvegarder les choix pour les questions à choix multiples/unique
                if question.question_type in ['single_choice', 'multiple_choice']:
                    choices = form.cleaned_data.get('choice_response')
                    # Debug prints
                    field_name_prefixed = f"{question.id}-choice_response"
                    print(f"Debug: Raw POST data for {field_name_prefixed} BEFORE workaround: {request.POST.getlist(field_name_prefixed)}")
                    field_name_unprefixed = "choice_response"
                    if not request.POST.getlist(field_name_prefixed) and request.POST.getlist(field_name_unprefixed):
                         if not hasattr(request.POST, '_mutable') or not request.POST._mutable:
                              request.POST._mutable = True
                         request.POST.setlist(field_name_prefixed, request.POST.getlist(field_name_unprefixed))
                         print(f"Debug: Assigned unprefixed {field_name_unprefixed} data to prefixed {field_name_prefixed}")
                    # Debug prints
                    print(f"Debug: Form for question {question.id} is bound: {form.is_bound}")
                    print(f"Debug: Form data for question {question.id}: {form.data}")
                    if question.question_type in ['single_choice', 'multiple_choice']:
                         field_name_in_form_data = f"{question.id}-choice_response"
                         print(f"Debug: Data in form.data for {field_name_in_form_data}: {form.data.getlist(field_name_in_form_data)}")

                    if choices:
                        if isinstance(choices, list):
                            response.choice_response.set(choices)
                        else:
                            # Even for single choice from ModelChoiceField, set expects iterable
                            response.choice_response.set([choices])

                # Debug print after setting ManyToManyField
                if question.question_type in ['single_choice', 'multiple_choice']:
                     print(f"Debug: response.choice_response.all() after setting ManyToMany: {list(response.choice_response.all())}")

            else:
                all_valid = False
                forms.append(form)
                # Debug: Print form errors
                print(f"Debug: Form errors for question {question.id}: {form.errors}")
        
        if all_valid:
            messages.success(request, 'Merci pour votre réponse!')
            return redirect('survey_app:survey_results', survey_id=survey.id)
        
        question_forms = [(question, form) for question, form in zip(questions, forms)]
        return render(request, 'survey_app/take_survey.html', {
            'survey': survey,
            'question_forms': question_forms
        })

class SurveyResultsView(View):
    def get(self, request, survey_id):
        survey = get_object_or_404(Survey, pk=survey_id)
        if request.user != survey.creator:
            messages.error(request, 'Vous n\'avez pas accès aux résultats de ce sondage.')
            return redirect('home')

        questions = Question.objects.filter(survey=survey)
        responses_by_question = {}

        for question in questions:
            # Fetch all responses for the current question
            responses_by_question[question] = Response.objects.filter(question=question).select_related('user').prefetch_related('choice_response')

        return render(request, 'survey_app/survey_results.html', {
            'survey': survey,
            'questions': questions,
            'responses_by_question': responses_by_question,
        })

@method_decorator(login_required, name='dispatch')
class ExportResultsView(View):
    def get(self, request, survey_id):
        survey = get_object_or_404(Survey, pk=survey_id)
        if request.user != survey.creator:
            messages.error(request, 'Vous n\'avez pas accès aux résultats de ce sondage.')
            return redirect('home')

        # Créer un buffer pour le PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Titre du sondage
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph(survey.title, title_style))
        elements.append(Spacer(1, 20))

        # Pour chaque question
        questions = Question.objects.filter(survey=survey)
        for question in questions:
            # Titre de la question
            elements.append(Paragraph(question.text, styles['Heading2']))
            elements.append(Spacer(1, 10))

            # Tableau des réponses
            responses = Response.objects.filter(question=question)
            data = [['Réponse', 'Date', 'Utilisateur']]  # En-tête du tableau

            for resp in responses:
                if question.question_type in ['single_choice', 'multiple_choice']:
                    if resp.choice_response is not None:
                        choices = resp.choice_response.all()
                        answer = ', '.join(choice.text for choice in choices)
                    else:
                        answer = 'Aucune réponse'
                elif question.question_type == 'scale':
                    answer = str(resp.scale_response) if resp.scale_response is not None else 'Aucune réponse'
                else:
                    answer = resp.text_response if resp.text_response else 'Aucune réponse'

                data.append([
                    answer,
                    resp.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    resp.user.username if resp.user else 'Anonyme'
                ])

            # Créer et styliser le tableau
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 30))

        # Générer le PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        # Créer la réponse HTTP
        response = HttpResponse(
            content_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{survey.title}_results.pdf"',
                'X-Frame-Options': 'DENY'
            }
        )
        response.write(pdf)
        return response