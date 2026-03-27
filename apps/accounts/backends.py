from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        try:
            # Try to fetch the user by searching the username or email field
            user = User.objects.get(username=username) if hasattr(User, 'username') and User.objects.filter(username=username).exists() else User.objects.get(email=username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user.
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
