from django.urls import path
from . import views

app_name = 'experiment'

urlpatterns = [
    # Page routes
    path('', views.landing, name='landing'),
    path('consent/', views.consent, name='consent'),
    path('demographics/', views.demographics, name='demographics'),
    path('tipi/', views.tipi, name='tipi'),
    path('pre-rating/<int:index>/', views.pre_rating, name='pre_rating'),
    path('chat/<int:index>/', views.chat, name='chat'),
    path('post-rating/<int:index>/', views.post_rating, name='post_rating'),
    path('debrief/', views.debrief, name='debrief'),
    path('complete/', views.complete, name='complete'),
    path('withdrawn/', views.withdrawn, name='withdrawn'),
    path('connection-error/', views.connection_error, name='connection_error'),

    # API routes
    path('api/chat/init/', views.chat_init, name='chat_init'),
    path('api/chat/send/', views.chat_send, name='chat_send'),
    path('api/chat/save/', views.chat_save, name='chat_save'),
    path('api/log-event/', views.log_event, name='log_event'),
    path('api/timer-expired/', views.timer_expired, name='timer_expired'),
]
