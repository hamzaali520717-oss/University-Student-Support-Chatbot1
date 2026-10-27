from django.shortcuts import get_object_or_404, render

from apps.academics import selectors as academics_selectors
from apps.admissions import selectors as admissions_selectors
from apps.content import selectors as content_selectors
from apps.finance import selectors as finance_selectors


def home(request):
    programs = list(academics_selectors.list_programs())
    context = {
        "hero_slides": content_selectors.list_active_hero_slides(),
        "featured_programs": programs[:6],
        "stats": {
            "programs": len(programs),
            "departments": academics_selectors.list_departments().count(),
            "scholarships": admissions_selectors.list_active_scholarships().count(),
            "deadlines": admissions_selectors.list_upcoming_deadlines().count(),
        },
        "announcements": content_selectors.list_published_announcements(audiences=["public"])[:4],
        "news": content_selectors.list_published_news()[:3],
    }
    return render(request, "website/home.html", context)


def program_list(request):
    programs = list(academics_selectors.list_programs_with_stats())
    # Only departments actually represented in the list get a filter chip,
    # so every chip is guaranteed to show at least one program.
    departments = academics_selectors.unique_departments_from_programs(programs=programs)
    context = {"programs": programs, "departments": departments}
    return render(request, "website/program_list.html", context)


def program_detail(request, code):
    program = get_object_or_404(academics_selectors.list_programs(), code=code)
    context = {
        "program": program,
        "subjects": academics_selectors.list_subjects(program_code=code),
        "requirements": admissions_selectors.list_requirements(program_code=code),
        "deadlines": admissions_selectors.list_upcoming_deadlines(program_code=code),
        "fee_structures": finance_selectors.list_fee_structures(program_code=code),
    }
    return render(request, "website/program_detail.html", context)


def scholarship_list(request):
    context = {"scholarships": list(admissions_selectors.list_active_scholarships())}
    return render(request, "website/scholarship_list.html", context)


def announcement_list(request):
    context = {
        "announcements": list(
            content_selectors.list_published_announcements(audiences=["public"])
        ),
    }
    return render(request, "website/announcement_list.html", context)


def news_list(request):
    context = {"news": list(content_selectors.list_published_news())}
    return render(request, "website/news_list.html", context)


def news_detail(request, slug):
    post = get_object_or_404(content_selectors.list_published_news(), slug=slug)
    return render(request, "website/news_detail.html", {"post": post})


def page_detail(request, slug):
    page = get_object_or_404(content_selectors.list_pages(), slug=slug)
    return render(request, "website/page_detail.html", {"page": page})


def contact(request):
    contact_page = content_selectors.get_page_by_slug(slug="contact")
    return render(request, "website/contact.html", {"contact_page": contact_page})
