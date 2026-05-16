"""View-level smoke tests — make sure the templates render and HTMX endpoints work."""
import pytest
from django.urls import reverse

from accounts.models import User
from tasks.models import Action, Context


@pytest.fixture
def user(db):
    return User.objects.create_user(email="donny@example.com", password="testpass1234!")


@pytest.fixture
def client_logged_in(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_root_redirects_anon_to_login(client):
    r = client.get(reverse("root"))
    assert r.status_code == 302
    assert "/accounts/login/" in r.url


@pytest.mark.django_db
def test_root_redirects_authed_to_inbox(client_logged_in):
    r = client_logged_in.get(reverse("root"))
    assert r.status_code == 302
    assert reverse("inbox") in r.url


@pytest.mark.django_db
def test_login_page_renders(client):
    r = client.get(reverse("accounts:login"))
    assert r.status_code == 200
    assert b"Sign in" in r.content


@pytest.mark.django_db
def test_signup_page_renders(client):
    r = client.get(reverse("accounts:signup"))
    assert r.status_code == 200
    assert b"Create your account" in r.content


@pytest.mark.django_db
def test_inbox_renders_empty(client_logged_in):
    r = client_logged_in.get(reverse("inbox"))
    assert r.status_code == 200
    assert b"Inbox" in r.content
    assert b"Inbox zero" in r.content


@pytest.mark.django_db
def test_next_actions_renders_empty(client_logged_in):
    r = client_logged_in.get(reverse("next_actions"))
    assert r.status_code == 200
    assert b"Next Actions" in r.content
    assert b"Nothing on deck" in r.content


@pytest.mark.django_db
def test_create_action(client_logged_in, user):
    r = client_logged_in.post(
        reverse("action_create"),
        {"title": "Buy milk"},
    )
    assert r.status_code == 200
    assert b"Buy milk" in r.content
    a = Action.objects.get(user=user)
    assert a.title == "Buy milk"
    assert a.status == Action.Status.INBOX


@pytest.mark.django_db
def test_complete_action_returns_row(client_logged_in, user):
    a = Action.objects.create(user=user, title="Test", status=Action.Status.NEXT)
    r = client_logged_in.post(reverse("action_complete", args=[a.pk]))
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.status == Action.Status.COMPLETED
    assert a.completed_at is not None


@pytest.mark.django_db
def test_process_inbox_to_next(client_logged_in, user):
    a = Action.objects.create(user=user, title="Test", status=Action.Status.INBOX)
    r = client_logged_in.post(reverse("action_move_to_next", args=[a.pk]))
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.status == Action.Status.NEXT


@pytest.mark.django_db
def test_delete_action(client_logged_in, user):
    a = Action.objects.create(user=user, title="Test")
    r = client_logged_in.post(reverse("action_delete", args=[a.pk]))
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.deleted_at is not None


@pytest.mark.django_db
def test_next_actions_grouped_by_context(client_logged_in, user):
    ctx = Context.objects.create(user=user, title="Home")
    Action.objects.create(user=user, title="Vacuum", status=Action.Status.NEXT, context=ctx)
    Action.objects.create(user=user, title="No context task", status=Action.Status.NEXT)
    r = client_logged_in.get(reverse("next_actions"))
    assert r.status_code == 200
    assert b"@Home" in r.content
    assert b"No context" in r.content
    assert b"Vacuum" in r.content


@pytest.mark.django_db
def test_user_cannot_touch_other_users_actions(client_logged_in, user):
    other = User.objects.create_user(email="other@example.com", password="testpass1234!")
    a = Action.objects.create(user=other, title="Not yours")
    r = client_logged_in.post(reverse("action_delete", args=[a.pk]))
    assert r.status_code == 404
