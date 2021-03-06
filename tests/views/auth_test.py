import json
import re

from allauth.account.models import EmailAddress

import pytest


CONFIRM_URL_RE = re.compile('(/auth/confirm/.+?/)')
PASSWORD_RESET_URL_RE = re.compile('/auth/password/reset/(.+?)/(.+?)/')


@pytest.mark.django_db()
def test_register_fine(client, mailoutbox, django_user_model):
    """Register user correctly."""

    NAME = 'item4'
    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'
    SUBJECT = '[item4.net] innocent 회원 가입을 위해 E-mail 주소를 확인해주세요!'
    res = client.post('/auth/register/', json.dumps({
        'name': NAME,
        'email': ADDRESS,
        'password1': PASSWORD,
        'password2': PASSWORD,
        'tz': 'Asia/Tokyo',
    }), content_type='application/json')
    data = res.json()
    assert data['detail'] == "Verification e-mail sent."

    address = EmailAddress.objects.get(email=ADDRESS)

    assert address
    assert not address.verified

    assert len(mailoutbox) == 1

    mail = mailoutbox[0]

    assert mail.subject == SUBJECT
    assert ADDRESS in mail.body
    assert list(mail.to) == [ADDRESS]

    match = CONFIRM_URL_RE.search(mail.body)
    assert match

    res = client.get(match.group(1))
    data = res.json()
    assert data['key']

    res = client.post('/auth/confirm/', json.dumps(data),
                      content_type='application/json')
    data = res.json()
    address.refresh_from_db()

    assert data['detail'] == 'ok'
    assert address.verified

    user = django_user_model.objects.get(email=ADDRESS)
    assert user.tz.zone == 'Asia/Tokyo'
    assert user.name == NAME


@pytest.mark.django_db()
def test_register_no_fields(client):
    """Register without fields"""

    res = client.post('/auth/register/', json.dumps({
    }), content_type='application/json')
    data = res.json()
    assert data['email'] == ['This field is required.']
    assert data['password1'] == ['This field is required.']
    assert data['password2'] == ['This field is required.']
    assert data['name'] == ['This field is required.']
    assert data['tz'] == ['This field is required.']


@pytest.mark.django_db()
def test_register_empty_fields(client):
    """Register with empty values"""

    res = client.post('/auth/register/', json.dumps({
        'name': '',
        'email': '',
        'password1': '',
        'password2': '',
        'tz': '',
    }), content_type='application/json')
    data = res.json()
    assert data['email'] == ['This field may not be blank.']
    assert data['password1'] == ['This field may not be blank.']
    assert data['password2'] == ['This field may not be blank.']
    assert data['name'] == ['This field may not be blank.']
    assert data['tz'] == ['This field may not be blank.']


@pytest.mark.django_db()
def test_register_invalid_email(client):
    """Register with invalid email"""

    NAME = 'item4'
    ADDRESS = 'invalid#example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'
    res = client.post('/auth/register/', json.dumps({
        'name': NAME,
        'email': ADDRESS,
        'password1': PASSWORD,
        'password2': PASSWORD,
        'tz': 'Asia/Tokyo',
    }), content_type='application/json')
    data = res.json()
    assert data['email'] == ['Enter a valid email address.']


@pytest.mark.django_db()
def test_register_invalid_password(client):
    """Register with invalid password"""

    NAME = 'item4'
    ADDRESS = 'item4@example.com'
    PASSWORD = '1234'
    res = client.post('/auth/register/', json.dumps({
        'name': NAME,
        'email': ADDRESS,
        'password1': PASSWORD,
        'password2': PASSWORD,
        'tz': 'Asia/Tokyo',
    }), content_type='application/json')
    data = res.json()
    assert data['password1'] == [
        'This password is too short. It must contain at least 16 characters.',
        'This password is too common.',
        'This password is entirely numeric.',
    ]


@pytest.mark.django_db()
def test_register_different_password(client):
    """Register with different password 1 and 2"""

    NAME = 'item4'
    ADDRESS = 'item4@example.com'
    res = client.post('/auth/register/', json.dumps({
        'name': NAME,
        'email': ADDRESS,
        'password1': '$uper$escret$uper$escret$uper$escret',  # used $
        'password2': 'supersescretsupersescretsupersescret',  # used s
        'tz': 'Asia/Tokyo',
    }), content_type='application/json')
    data = res.json()
    assert data['non_field_errors'] == [
        "The two password fields didn't match.",
    ]


@pytest.mark.django_db()
def test_register_long_name(client):
    """Register with too long name"""

    NAME = 'item' + '4'*100
    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'
    res = client.post('/auth/register/', json.dumps({
        'name': NAME,
        'email': ADDRESS,
        'password1': PASSWORD,
        'password2': PASSWORD,
        'tz': 'Asia/Tokyo',
    }), content_type='application/json')
    data = res.json()
    assert data['name'] == [
        'Ensure this field has no more than 25 characters.',
    ]


@pytest.mark.django_db()
def test_login_fine(rf, django_user_model, client):
    """Login successfully"""

    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'

    user = django_user_model.objects.create_user(ADDRESS, PASSWORD)
    request = rf.get('/')
    address = EmailAddress.objects.add_email(request, user, ADDRESS)
    address.verified = True
    address.save()

    res = client.post('/auth/login/', json.dumps({
        'email': ADDRESS,
        'password': PASSWORD,
    }), content_type='application/json')
    data = res.json()
    assert data['key']


@pytest.mark.django_db()
def test_login_no_verified(rf, django_user_model, client):
    """Login with no-verified account"""

    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'

    user = django_user_model.objects.create_user(ADDRESS, PASSWORD)
    request = rf.get('/')
    EmailAddress.objects.add_email(request, user, ADDRESS)

    res = client.post('/auth/login/', json.dumps({
        'email': ADDRESS,
        'password': PASSWORD,
    }), content_type='application/json')
    data = res.json()
    assert data['non_field_errors'] == ['E-mail is not verified.']


@pytest.mark.django_db()
def test_login_wrong_email(client):
    """Login with wrong email"""

    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'

    res = client.post('/auth/login/', json.dumps({
        'email': ADDRESS,
        'password': PASSWORD,
    }), content_type='application/json')
    data = res.json()
    assert data['non_field_errors'] == [
        'Unable to log in with provided credentials.',
    ]


@pytest.mark.django_db()
def test_login_wrong_password(rf, django_user_model, client):
    """Login with wrong password"""

    ADDRESS = 'item4@example.com'
    PASSWORD = '$uper$escret$uper$escret$uper$escret'

    user = django_user_model.objects.create_user(ADDRESS, PASSWORD)
    request = rf.get('/')
    address = EmailAddress.objects.add_email(request, user, ADDRESS)
    address.verified = True
    address.save()

    res = client.post('/auth/login/', json.dumps({
        'email': ADDRESS,
        'password': 'wrongpa$$wordwrongpa$$wordwrongpa$$word',
    }), content_type='application/json')
    data = res.json()
    assert data['non_field_errors'] == [
        'Unable to log in with provided credentials.',
    ]


@pytest.mark.django_db()
def test_logout(client):
    """Logout"""

    res = client.post('/auth/logout/', json.dumps({}),
                      content_type='application/json')
    data = res.json()
    assert data['detail'] == 'Successfully logged out.'


@pytest.mark.django_db()
def test_password_reset_fine(client, django_user_model, mailoutbox):
    """Password reset"""

    ADDRESS = 'item4@example.com'
    OLD_PASSWORD = '$uper$escret$uper$escret$uper$escret'
    NEW_PASSWORD = 'nEwpa$$wordnEwpa$$wordnEwpa$$word'
    SUBJECT = 'innocent(item4.net) 비밀번호 리셋 요청'

    user = django_user_model.objects.create_user(ADDRESS, OLD_PASSWORD)

    res = client.post('/auth/password/reset/', {
        'email': ADDRESS,
    })
    data = res.json()
    assert data['detail'] == 'Password reset e-mail has been sent.'

    mail = mailoutbox[0]

    assert mail.subject == SUBJECT
    assert list(mail.to) == [ADDRESS]

    match = PASSWORD_RESET_URL_RE.search(mail.body)
    assert match

    res = client.post('/auth/password/reset/confirm/', {
        'new_password1': NEW_PASSWORD,
        'new_password2': NEW_PASSWORD,
        'uid': match.group(1),
        'token': match.group(2),
    })
    data = res.json()
    assert data['detail'] == 'Password has been reset with the new password.'

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


@pytest.mark.django_db()
def test_password_change_fine(client, django_user_model):
    """Password change"""

    ADDRESS = 'item4@example.com'
    OLD_PASSWORD = '$uper$escret$uper$escret$uper$escret'
    NEW_PASSWORD = 'nEwpa$$wordnEwpa$$wordnEwpa$$word'

    user = django_user_model.objects.create_user(ADDRESS, OLD_PASSWORD)
    client.login(email=ADDRESS, password=OLD_PASSWORD)

    res = client.post('/auth/password/change/', {
        'old_password': OLD_PASSWORD,
        'new_password1': NEW_PASSWORD,
        'new_password2': NEW_PASSWORD,
    })
    data = res.json()
    assert data['detail'] == 'New password has been saved.'

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
