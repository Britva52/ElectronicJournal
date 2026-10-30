from django.shortcuts import render


def csrf_failure(request, reason=''):
    # Не показываем внутренние диагностические сведения или пользовательские данные.
    return render(request, 'registration/preview_csrf_failure.html', status=403)
