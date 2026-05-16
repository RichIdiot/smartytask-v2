"""Auth forms."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Preferences, User


class TailwindMixin:
    """Apply Tailwind classes to every field widget."""

    base_classes = (
        "block w-full rounded-lg border border-slate-300 bg-white px-4 py-3 "
        "text-[17px] text-slate-900 shadow-sm "
        "focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{self.base_classes} {existing}".strip()
            field.widget.attrs.setdefault("autocomplete", _autocomplete_for(name))


def _autocomplete_for(name: str) -> str:
    mapping = {
        "email": "email",
        "password": "current-password",
        "password1": "new-password",
        "password2": "new-password",
        "first_name": "given-name",
        "last_name": "family-name",
    }
    return mapping.get(name, "off")


class SignupForm(TailwindMixin, UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=60, required=False, label="First name")

    class Meta:
        model = User
        fields = ("email", "first_name", "password1", "password2")

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        if commit:
            user.save()
            Preferences.objects.create(user=user)
        return user


class LoginForm(TailwindMixin, AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput())
