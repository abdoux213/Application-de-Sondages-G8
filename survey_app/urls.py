from django.urls import path
from . import views

app_name = 'survey_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('create/', views.SurveyCreateView.as_view(), name='survey_create'),
    path('<int:survey_id>/', views.SurveyDetailView.as_view(), name='survey_detail'),
    path('<int:survey_id>/take/', views.TakeSurveyView.as_view(), name='take_survey'),
    path('<int:survey_id>/results/', views.SurveyResultsView.as_view(), name='survey_results'),
    path('<int:survey_id>/add-question/', views.AddQuestionView.as_view(), name='add_question'),
    path('<int:survey_id>/export/', views.ExportResultsView.as_view(), name='export_results'),
]