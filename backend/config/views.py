from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView

from analysis.models import JobMatch
from analysis.services import AnalysisService
from recommendations.models import CareerRecommendation
from resumes.extraction import extract_text_from_file
from resumes.models import Resume


class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username sudah digunakan.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email sudah digunakan.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Password dan konfirmasi password tidak cocok.")
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )
        return user


class HomeView(TemplateView):
    template_name = "home/index.html"
    extra_context = {"page_name": "home"}


class LoginView(View):
    template_name = "auth/login.html"

    def get(self, request):
        form = AuthenticationForm()
        return render(request, self.template_name, {"form": form, "page_name": "login"})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("/dashboard/")
        return render(request, self.template_name, {"form": form, "page_name": "login"})


class RegisterView(View):
    template_name = "auth/register.html"

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {"form": form, "page_name": "register"})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("/dashboard/")
        return render(request, self.template_name, {"form": form, "page_name": "register"})


class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        return redirect("/")


class AnalyzerFormView(LoginRequiredMixin, View):
    template_name = "analyzer/form.html"
    login_url = "/login/"

    def get(self, request):
        from django import forms

        class CVForm(forms.Form):
            cv_file = forms.FileField()

        class JobForm(forms.Form):
            job_description = forms.CharField(widget=forms.Textarea, required=False)

        cv_form = CVForm()
        job_form = JobForm()
        return render(
            request,
            self.template_name,
            {"cv_form": cv_form, "job_form": job_form, "page_name": "analyzer"},
        )

    def post(self, request):
        from django import forms

        class CVForm(forms.Form):
            cv_file = forms.FileField()

        class JobForm(forms.Form):
            job_description = forms.CharField(widget=forms.Textarea, required=False)

        cv_form = CVForm(request.POST, request.FILES)
        job_form = JobForm(request.POST)

        if cv_form.is_valid() and job_form.is_valid():
            cv_file = cv_form.cleaned_data["cv_file"]
            job_text = job_form.cleaned_data.get("job_description", "").strip()

            if not job_text:
                job_form.add_error("job_description", "Job description wajib diisi untuk mode CV vs Job")
            else:
                try:
                    # Extract text from CV
                    extracted_text = extract_text_from_file(cv_file)
                    
                    if not extracted_text or not extracted_text.strip():
                        cv_form.add_error("cv_file", "Tidak dapat mengekstrak teks dari file CV")
                    else:
                        # Run analysis
                        analysis_result = AnalysisService.analyze_cv_vs_job(
                            cv_text=extracted_text,
                            job_text=job_text,
                            cv_filename=cv_file.name
                        )
                        
                        # Save resume
                        resume = Resume.objects.create(
                            user=request.user,
                            original_filename=cv_file.name,
                            cv_file=cv_file,
                            extracted_text=extracted_text,
                        )
                        
                        # Save job match
                        job_match = JobMatch.objects.create(
                            user=request.user,
                            resume=resume,
                            job_title_target=None,
                            job_description_text=job_text,
                            compatibility_score=analysis_result["compatibility_score"],
                            compatibility_level=analysis_result["compatibility_level"],
                            semantic_score=analysis_result["semantic_score"],
                            skill_score=analysis_result["skill_score"],
                            experience_score=analysis_result["experience_score"],
                            education_score=analysis_result["education_score"],
                            matched_skills=analysis_result["matched_skills"],
                            missing_skills=analysis_result["missing_skills"],
                            recommendations=analysis_result["recommendations"],
                        )
                        
                        return redirect("analyzer-result", analysis_id=job_match.id)
                        
                except ValueError as e:
                    cv_form.add_error("cv_file", str(e))
                except Exception as e:
                    cv_form.add_error("cv_file", f"Error saat analisis: {str(e)}")

        return render(
            request,
            self.template_name,
            {"cv_form": cv_form, "job_form": job_form, "page_name": "analyzer"},
        )


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"
    login_url = "/login/"
    extra_context = {"page_name": "dashboard"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's resumes
        resumes = Resume.objects.filter(user=user).order_by("-uploaded_at")

        # Get user's job matches
        matches = JobMatch.objects.filter(user=user).order_by("-created_at")[:10]

        # Get user's career recommendations
        recommendations = CareerRecommendation.objects.filter(user=user).order_by(
            "-created_at"
        )[:10]

        # Calculate stats
        total_analyses = matches.count() + recommendations.count()
        average_score = 0
        if matches.exists():
            average_score = sum(
                float(m.compatibility_score) for m in matches
            ) / matches.count()
        top_role = "-"
        if recommendations.exists():
            top_role = recommendations.first().dominant_category

        context["stats"] = {
            "total_analyses": total_analyses,
            "average_score": average_score / 100 if average_score else 0,
            "top_role": top_role,
        }

        # Combine and format analyses for the template
        analyses_list = []
        for match in matches:
            analyses_list.append(
                {
                    "id": str(match.id),
                    "cv_file": match.resume.original_filename,
                    "mode": "CV vs Job",
                    "compatibility_score": float(match.compatibility_score)
                    / 100,
                    "compatibility_level": match.compatibility_level,
                    "created_at": match.created_at.isoformat(),
                }
            )

        for rec in recommendations:
            top_roles = rec.top_roles.all()
            top_role_title = top_roles.first().role_title if top_roles.exists() else "-"
            analyses_list.append(
                {
                    "id": str(rec.id),
                    "cv_file": rec.resume.original_filename,
                    "mode": "Career",
                    "compatibility_score": 0,
                    "compatibility_level": rec.dominant_category,
                    "created_at": rec.created_at.isoformat(),
                }
            )

        # Sort by created_at descending
        analyses_list.sort(key=lambda x: x["created_at"], reverse=True)
        context["analyses"] = analyses_list[:10]

        return context


class AnalyzerResultView(LoginRequiredMixin, TemplateView):
    template_name = "analyzer/result.html"
    login_url = "/login/"
    extra_context = {"page_name": "result"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analysis_id = kwargs.get("analysis_id")

        try:
            match = JobMatch.objects.get(id=analysis_id, user=self.request.user)
            context["analysis"] = {
                "id": str(match.id),
                "cv_file": match.resume.original_filename,
                "mode": "CV vs Job",
                "compatibility_score": float(match.compatibility_score) / 100,
                "compatibility_level": match.compatibility_level,
                "created_at": match.created_at.isoformat(),
                "processing_time_ms": 0,
                "skill_gap_matched": match.matched_skills,
                "skill_gap_missing": match.missing_skills,
                "top_roles": [],
                "roadmap": [],
            }
        except JobMatch.DoesNotExist:
            try:
                rec = CareerRecommendation.objects.get(
                    id=analysis_id, user=self.request.user
                )
                top_roles = rec.top_roles.all()
                context["analysis"] = {
                    "id": str(rec.id),
                    "cv_file": rec.resume.original_filename,
                    "mode": "Career",
                    "compatibility_score": 0,
                    "compatibility_level": rec.dominant_category,
                    "created_at": rec.created_at.isoformat(),
                    "processing_time_ms": 0,
                    "skill_gap_matched": [],
                    "skill_gap_missing": [],
                    "top_roles": [
                        {"role": r.role_title, "score": float(r.match_percentage) / 100}
                        for r in top_roles
                    ],
                    "roadmap": rec.learning_path,
                }
            except CareerRecommendation.DoesNotExist:
                context["analysis"] = {}

        return context


class AboutView(TemplateView):
    template_name = "about/index.html"
    extra_context = {"page_name": "about"}


class HelpView(TemplateView):
    template_name = "help/index.html"
    extra_context = {"page_name": "help"}


class PrivacyView(TemplateView):
    template_name = "privacy/index.html"
    extra_context = {"page_name": "privacy"}