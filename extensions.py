# extensions.py – Shared Flask extensions and AI client singleton
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from openai import OpenAI
from authlib.integrations.flask_client import OAuth

# ── Flask extensions (initialized without app; app bound via init_app) ────────
db             = SQLAlchemy()
login_manager  = LoginManager()
login_manager.login_view = 'login'
oauth          = OAuth()


# ── Dynamic AI client Proxy ───────────────────────────────────────────────────
class DynamicAIClient:
    @property
    def _client(self):
        from models import SystemSetting
        provider = SystemSetting.get('active_ai_provider', 'openrouter')

        if provider == 'openai':
            api_key = SystemSetting.get('openai_api_key', '').strip()
            if not api_key:
                raise RuntimeError('Chưa cấu hình OpenAI API key trong Admin → Cài đặt.')
            return OpenAI(api_key=api_key)

        if provider == 'gemini':
            api_key = SystemSetting.get('gemini_api_key', '').strip()
            if not api_key:
                raise RuntimeError('Chưa cấu hình Gemini API key trong Admin → Cài đặt.')
            return OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

        api_key = SystemSetting.get('openrouter_api_key', '').strip()
        if not api_key:
            raise RuntimeError('Chưa cấu hình OpenRouter API key trong Admin → Cài đặt.')
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def __getattr__(self, name):
        return getattr(self._client, name)


ai_client = DynamicAIClient()
