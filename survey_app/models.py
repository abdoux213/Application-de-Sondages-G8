from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class Survey(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    password = models.CharField(max_length=100, blank=True, null=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    max_responses = models.IntegerField(default=0)  # 0 means unlimited
    template = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPES = [
        ('single_choice', 'Choix unique'),
        ('multiple_choice', 'Choix multiple'),
        ('scale', 'Échelle'),
        ('text', 'Texte libre'),
    ]
    
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500, default='')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    required = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    conditional_question = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    conditional_value = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200, default='')
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    text_response = models.TextField(blank=True, null=True)
    choice_response = models.ManyToManyField(Choice, blank=True)
    scale_response = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Response to {self.question.text}"

class SurveyShare(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    share_token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Share link for {self.survey.title}"

class SurveyNotification(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    notify_on_response = models.BooleanField(default=True)
    notify_on_completion = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Notifications for {self.user.username} - {self.survey.title}"