"""Smoke tests — verify the scaffold actually boots."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthz(client):
    response = client.get(reverse("healthz"))
    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_user_model_exists():
    from accounts.models import User
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_action_model_status_choices():
    from tasks.models import Action
    expected = {"inbox", "next", "scheduled", "waiting", "someday", "tickler", "completed"}
    assert set(Action.Status.values) == expected
