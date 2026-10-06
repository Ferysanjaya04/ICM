from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def about(request):
    return render(request, 'about/index.html')


@require_http_methods(["GET"])
def help_page(request):
    return render(request, 'help/index.html')


@require_http_methods(["GET"])
def privacy(request):
    return render(request, 'privacy/index.html')
