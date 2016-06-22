# -*- coding: utf-8 -*-
from django.conf.urls import url, patterns, include
from django.core.urlresolvers import reverse_lazy
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView
#from django.views.generic.edit import CreateView
#from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin
from .views import RegisterView, ChooseGameView, PlayGameView, DeckEditorView
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^play_game/$', PlayGameView.as_view(), name='play_game'),
    url(r'^choose_game/$', ChooseGameView.as_view(), name='choose_game'),
    url(r'^deck_editor/$', DeckEditorView.as_view(), name='deck_editor'),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    #url('^register/', CreateView.as_view(
    #        template_name='register.html',
    #        form_class=UserCreationForm,
    #        success_url='/'
    #)),
    url('^accounts/', include('django.contrib.auth.urls')),
    url(r'^[/]?$', RedirectView.as_view(url='/choose_game/')),
    url(r'^chat/$', RedirectView.as_view(url='/choose_game/')),
) + staticfiles_urlpatterns()
