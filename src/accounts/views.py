"""Auth views."""
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignupForm


class SignupView(CreateView):
    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("inbox")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("inbox")
        return super().get(request, *args, **kwargs)
