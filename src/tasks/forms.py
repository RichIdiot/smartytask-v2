"""Forms for the tasks app."""
from django import forms

from .models import Action


class QuickAddActionForm(forms.ModelForm):
    """The compact 'capture' form on Inbox/Next Actions pages."""

    class Meta:
        model = Action
        fields = ("title",)
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "What needs to get done?",
                    "autocomplete": "off",
                    "class": (
                        "block w-full rounded-lg border border-slate-300 bg-white "
                        "px-4 py-3.5 text-[17px] text-slate-900 shadow-sm "
                        "focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/40"
                    ),
                }
            ),
        }


class ActionEditForm(forms.ModelForm):
    """Full edit form for an action."""

    class Meta:
        model = Action
        fields = (
            "title", "notes", "status", "context", "project",
            "someday_list", "effort", "minutes_required", "due_date", "starred",
        )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["context"].queryset = self.fields["context"].queryset.filter(user=user)
            self.fields["project"].queryset = self.fields["project"].queryset.filter(
                user=user, deleted_at__isnull=True
            )
            self.fields["someday_list"].queryset = self.fields["someday_list"].queryset.filter(
                user=user
            )
