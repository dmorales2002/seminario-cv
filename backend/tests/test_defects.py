import os

os.environ.setdefault("SECRET_KEY", "clave-solo-para-pruebas-" + "x" * 32)

import io
import unittest
from datetime import timedelta

import jwt
from pydantic import ValidationError
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.core.config import Settings, settings
from app.core.security import create_access_token
from app.schemas.user import UserCreate
from app.services.extractor import extract_text_from_pdf


class SecretKeyTests(unittest.TestCase):
    def test_short_or_example_secret_is_rejected(self):
        for value in ("corta", "SUPER_SECRET_KEY_FOR_MVP_2026_REPLACE_IN_PRODUCTION", "replace-with-a-long-random-secret"):
            with self.assertRaises(ValidationError):
                Settings(SECRET_KEY=value, _env_file=None)

    def test_long_secret_is_accepted_and_sessions_are_short(self):
        configured = Settings(SECRET_KEY="k" * 40, _env_file=None)
        self.assertEqual(configured.ACCESS_TOKEN_EXPIRE_MINUTES, 480)


class PasswordPolicyTests(unittest.TestCase):
    def _user(self, password):
        return UserCreate(full_name="Ana", email="ana@example.com", password=password, role="CANDIDATE")

    def test_rejects_short_and_weak_passwords(self):
        for password in ("a", "corta1", "soloLetrasLargas", "123456789"):
            with self.assertRaises(ValidationError, msg=password):
                self._user(password)

    def test_accepts_password_with_letters_and_numbers(self):
        self.assertEqual(self._user("Segura2026x").password, "Segura2026x")


class TokenTests(unittest.TestCase):
    def test_token_round_trip_with_pyjwt(self):
        token = create_access_token({"sub": "abc"}, timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        self.assertEqual(payload["sub"], "abc")

    def test_expired_token_is_rejected(self):
        token = create_access_token({"sub": "abc"}, timedelta(minutes=-1))
        with self.assertRaises(jwt.PyJWTError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


class PdfSpacingTests(unittest.TestCase):
    def test_words_with_tight_spacing_keep_their_spaces(self):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        x = 72
        for word in ("Administración", "de", "bases", "de", "datos"):
            pdf.drawString(x, 700, word)
            x += stringWidth(word, "Helvetica", 12) + 2  # separación menor que la tolerancia predeterminada
        pdf.save()
        text = extract_text_from_pdf(buffer.getvalue())
        self.assertEqual(text, "Administración de bases de datos")


class PasswordRecoveryTests(unittest.TestCase):
    def test_recovery_endpoint_is_honest_about_not_being_implemented(self):
        from fastapi.testclient import TestClient
        from app.main import app
        response = TestClient(app).post("/api/v1/auth/password-recovery", params={"email": "ana@example.com"})
        self.assertEqual(response.status_code, 501)


if __name__ == "__main__":
    unittest.main()
