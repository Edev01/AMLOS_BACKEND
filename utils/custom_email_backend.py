import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend

class UnverifiedSMTP(smtplib.SMTP):
    def starttls(self, *args, **kwargs):
        # Unconditionally force unverified SSL context to bypass macOS cert validation
        kwargs['context'] = ssl._create_unverified_context()
        return super().starttls(*args, **kwargs)

class SSLBypassEmailBackend(EmailBackend):
    @property
    def connection_class(self):
        return UnverifiedSMTP
