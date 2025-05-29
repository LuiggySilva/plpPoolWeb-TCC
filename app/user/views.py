from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.messages import constants
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required

from . import models, forms, utils


@login_required
def profile(request):
    return render(request, 'user/profile.html', context={})