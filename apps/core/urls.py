from django.urls import path

from .views import (
    AboutView,
    ContactView,
    DevenirGuideView,
    FaqView,
    HomeView,
    LegalPageView,
    NewsletterSubscribeView,
)

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("a-propos/", AboutView.as_view(), name="about"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("faq/", FaqView.as_view(), name="faq"),
    path("devenir-guide/", DevenirGuideView.as_view(), name="become_guide"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="newsletter"),
    path("mentions-legales/", LegalPageView.as_view(page_key="mentions"), name="mentions_legales"),
    path("confidentialite/", LegalPageView.as_view(page_key="confidentialite"), name="confidentialite"),
    path("cgv/", LegalPageView.as_view(page_key="cgv"), name="cgv"),
]
