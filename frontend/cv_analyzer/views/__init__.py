"""Per-feature views package. Diimpor urls.py sebagai `views`."""
from .accounts import user_login, user_logout, user_register
from .analyzer import analysis_results, cv_analyzer
from .api import api_match_cv, api_recommend_career
from .dashboard import dashboard
from .home import home
from .pages import about, help_page, privacy

__all__ = [
    "home",
    "user_login", "user_register", "user_logout",
    "dashboard",
    "cv_analyzer", "analysis_results",
    "about", "help_page", "privacy",
    "api_match_cv", "api_recommend_career",
]
