from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY', default='change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
#ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
ALLOWED_HOSTS = ['marcosmatica.pythonanywhere.com', 'localhost', '127.0.0.1']

'''
if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
else:
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='marcosmatica.pythonanywhere.com').split(',')
'''
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'viewflow.fsm',
    'auditlog',
    #'import_export',
    'crispy_forms',
    'crispy_tailwind',
    'core',
    #'wagtail',
    'pedagogico',
    'atendimentos',
    'napne',
    'projetos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
]

ROOT_URLCONF = 'ocorrencias_ifb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ocorrencias_ifb.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='ocorrencias_ifb'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='62726748'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
'''
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

LOGIN_URL = '/login/'  # Agora ambas as URLs funcionam
LOGIN_REDIRECT_URL = '/dashboard/'  # Onde redirecionar após login
LOGOUT_REDIRECT_URL = '/'  # Onde redirecionar após logout

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Ou a URL do seu broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' # Opcional: armazena os resultados das tarefas
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo' # Defina seu timezone

# Security
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    ALLOWED_HOSTS = ['marcosmatica.pythonanywhere.com', 'localhost', '127.0.0.1']



#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Configurações de Email para recuperação de senha
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Ou seu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = '3353645@etfbsb.edu.br'
EMAIL_HOST_PASSWORD = 'lckx iwes sydo xkrw'
#DEFAULT_FROM_EMAIL = '3353645@etfbsb.edu.br'
EMAIL_TIMEOUT = 30  # Aumenta o timeout

DEFAULT_FROM_EMAIL = 'Coordenações DREP IFB Recanto das Emas <no-reply@ifb.edu.br>'
SERVER_EMAIL = 'Coordenações DREP IFB Recanto das Emas <no-reply@ifb.edu.br>'

# Se quiser manter o email atual como fallback, adicione também:
EMAIL_FROM_NAME = 'Coordenações DREP IFB Recanto das Emas'
EMAIL_FROM_ADDRESS = 'no-reply@ifb.edu.br'

EMAIL_TEMPLATE_NAME = 'registration/password_reset_email.html'
EMAIL_SUBJECT_TEMPLATE_NAME = 'registration/password_reset_subject.txt'

EMAIL_SUBJECT_PREFIX = '[Sistema DREP IFB Recanto das Emas] '

# LGPD - Retenção de dados
DATA_RETENTION_YEARS = 5


#TEMPO DE SESSAO
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 60 * 5
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ===== CONFIGURAÇÃO TWILIO (SMS) =====
# Opção 1: Twilio (internacional, mais conhecido)
TWILIO_ACCOUNT_SID = 'AC1be6f3e15431e83f0e92af9f3ca832d3'  # Obter em twilio.com
TWILIO_AUTH_TOKEN = '7bc7fc38cd046a808488baf460c6a722'
TWILIO_PHONE_NUMBER = '+12769457728'  # Número Twilio

# ===== CONFIGURAÇÃO ZENVIA (SMS) =====
# Opção 2: Zenvia (brasileiro, aceita números BR)
ZENVIA_API_TOKEN = 'seu_token_zenvia'  # Obter em zenvia.com
ZENVIA_SENDER_ID = 'IFB'  # Nome que aparece no SMS

# ===== OUTRAS OPÇÕES DE SMS BRASILEIRAS =====
# - Total Voice: https://totalvoice.com.br/
# - Movile SMS: https://www.movile.com/sms/
# - SMS Brasil: https://www.smsbrasil.com.br/

# Para desenvolvimento/testes sem SMS real:
# Comente as configurações acima e o sistema apenas imprimirá logs