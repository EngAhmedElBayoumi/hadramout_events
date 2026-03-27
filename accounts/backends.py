from django.contrib.auth.backends import ModelBackend
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either
    username or email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try to find user by username first
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Try by email
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
