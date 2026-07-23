from django.urls import path

from user_feedback import views

# One generic endpoint for saving any experiment's feedback.
urlpatterns = [
    path("submit/", views.submit, name="user-feedback-submit"),
    path("modal/", views.modal, name="user-feedback-modal"),
    path("opt-out/", views.opt_out, name="user-feedback-opt-out"),
]
