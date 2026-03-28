import pytest
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import OTPCode
from apps.accounts.tasks import cleanup_expired_otps
from tests.factories import OTPCodeFactory

@pytest.mark.django_db
def test_cleanup_expired_otps():
    # Create an old OTP
    old_otp = OTPCodeFactory()
    # Manually update created_at as auto_now_add prevents setting it in create
    OTPCode.objects.filter(id=old_otp.id).update(created_at=timezone.now() - timedelta(hours=30))
    
    # Create a fresh OTP
    fresh_otp = OTPCodeFactory()
    
    result = cleanup_expired_otps()
    assert "Deleted 1" in result
    assert not OTPCode.objects.filter(id=old_otp.id).exists()
    assert OTPCode.objects.filter(id=fresh_otp.id).exists()
