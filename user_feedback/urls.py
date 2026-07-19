from django.urls import path

from user_feedback import views

# One generic endpoint for saving any experiment's feedback.
urlpatterns = [
    path("submit/", views.submit, name="user-feedback-submit"),
]
