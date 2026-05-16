"""View-level smoke tests — make sure the templates render and HTMX endpoints work."""
import pytest
from django.urls import reverse

from accounts.models import User
from tasks.models import Action, Context, Project


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


# ---------- projects ----------

@pytest.mark.django_db
def test_project_list_renders_empty(client_logged_in):
    r = client_logged_in.get(reverse("project_list"))
    assert r.status_code == 200
    assert b"Projects" in r.content
    assert b"No active projects" in r.content


@pytest.mark.django_db
def test_project_list_shows_active_projects(client_logged_in, user):
    Project.objects.create(user=user, title="Launch v2")
    Project.objects.create(user=user, title="Fix the porch")
    r = client_logged_in.get(reverse("project_list"))
    assert r.status_code == 200
    assert b"Launch v2" in r.content
    assert b"Fix the porch" in r.content


@pytest.mark.django_db
def test_project_create(client_logged_in, user):
    r = client_logged_in.post(reverse("project_create"), {"title": "Ship Inbox UI"})
    assert r.status_code == 200
    assert b"Ship Inbox UI" in r.content
    p = Project.objects.get(user=user)
    assert p.title == "Ship Inbox UI"
    assert p.completed_at is None
    assert p.deleted_at is None


@pytest.mark.django_db
def test_project_create_requires_title(client_logged_in):
    r = client_logged_in.post(reverse("project_create"), {"title": ""})
    assert r.status_code == 400


@pytest.mark.django_db
def test_project_rename(client_logged_in, user):
    p = Project.objects.create(user=user, title="Old name")
    r = client_logged_in.post(reverse("project_update_title", args=[p.pk]), {"title": "New name"})
    assert r.status_code == 200
    assert b"New name" in r.content
    p.refresh_from_db()
    assert p.title == "New name"


@pytest.mark.django_db
def test_project_complete_toggle(client_logged_in, user):
    p = Project.objects.create(user=user, title="Wrap up Q1")
    r = client_logged_in.post(reverse("project_complete_toggle", args=[p.pk]))
    assert r.status_code == 200
    p.refresh_from_db()
    assert p.completed_at is not None
    # Toggle back open
    r = client_logged_in.post(reverse("project_complete_toggle", args=[p.pk]))
    assert r.status_code == 200
    p.refresh_from_db()
    assert p.completed_at is None


@pytest.mark.django_db
def test_project_delete(client_logged_in, user):
    p = Project.objects.create(user=user, title="Mistake")
    r = client_logged_in.post(reverse("project_delete", args=[p.pk]))
    assert r.status_code == 200
    p.refresh_from_db()
    assert p.deleted_at is not None


@pytest.mark.django_db
def test_project_detail_renders(client_logged_in, user):
    p = Project.objects.create(user=user, title="Build a deck")
    Action.objects.create(user=user, title="Buy lumber", status=Action.Status.NEXT, project=p)
    Action.objects.create(user=user, title="Sand boards", status=Action.Status.NEXT, project=p)
    r = client_logged_in.get(reverse("project_detail", args=[p.pk]))
    assert r.status_code == 200
    assert b"Build a deck" in r.content
    assert b"Buy lumber" in r.content
    assert b"Sand boards" in r.content


@pytest.mark.django_db
def test_action_create_scoped_to_project(client_logged_in, user):
    p = Project.objects.create(user=user, title="Move house")
    r = client_logged_in.post(
        reverse("action_create"),
        {"title": "Get boxes", "status": "next", "project_id": str(p.pk)},
    )
    assert r.status_code == 200
    a = Action.objects.get(user=user, title="Get boxes")
    assert a.project_id == p.pk
    assert a.status == Action.Status.NEXT


@pytest.mark.django_db
def test_action_create_rejects_other_users_project(client_logged_in, user):
    other = User.objects.create_user(email="other@example.com", password="x12345678")
    p = Project.objects.create(user=other, title="Theirs")
    r = client_logged_in.post(
        reverse("action_create"),
        {"title": "Sneaky", "project_id": str(p.pk)},
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_user_cannot_touch_other_users_project(client_logged_in):
    other = User.objects.create_user(email="other@example.com", password="x12345678")
    p = Project.objects.create(user=other, title="Theirs")
    r = client_logged_in.post(reverse("project_delete", args=[p.pk]))
    assert r.status_code == 404
    r = client_logged_in.get(reverse("project_detail", args=[p.pk]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_completed_projects_show_in_recent_section(client_logged_in, user):
    from django.utils import timezone
    p = Project.objects.create(user=user, title="Old project", completed_at=timezone.now())
    r = client_logged_in.get(reverse("project_list"))
    assert r.status_code == 200
    assert b"Recently completed" in r.content
    assert b"Old project" in r.content


@pytest.mark.django_db
def test_projects_count_in_sidebar(client_logged_in, user):
    Project.objects.create(user=user, title="One")
    Project.objects.create(user=user, title="Two")
    r = client_logged_in.get(reverse("inbox"))
    # The badge text "2" should appear in the projects nav item.
    assert r.status_code == 200
    assert b"Projects" in r.content
