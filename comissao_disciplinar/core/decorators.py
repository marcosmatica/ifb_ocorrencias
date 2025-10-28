# core/decorators.py (criar)

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages


def coordenacao_required(coordenacoes):
    """Decorator para verificar se servidor pertence a coordenações específicas"""

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'servidor'):
                messages.error(request, 'Acesso negado.')
                return redirect('home')

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if request.user.servidor.coordenacao in coordenacoes:
                return view_func(request, *args, **kwargs)

            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('dashboard')

        return wrapper

    return decorator

# Uso:
# @coordenacao_required(['CDPD', 'CC', 'CGEN'])
# def alguma_view(request):
#     ...