from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin


app_name = 'main'


urlpatterns = [
    path('', views.home, name='home'),
    path('test/', views.test, name='test'),
    path('lobby/', views.lobby, name='lobby'),
    path('questionbank/', views.questionbank, name='questionbank'),
    path('question/<int:question_id>/', views.question_answer, name='question_answer'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('zens/', views.zen, name='zens'),
    path('submit-exam/', views.submit_exam, name='submit_exam'),
    path('profile/', views.profile, name='profile'),
    path('feedback/', views.feedback, name="feedback"),
    path('ai-tools/', views.tools, name="tools"),
    path('lit-devices/', views.lit_devices, name="lit_devices"),
    path('lit-search/', views.lit_search, name="lit_search"),
    path('save-highlight/', views.save_highlight, name='save_highlight'),

]
