from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'field'
        self.fields['password1'].widget.attrs['type'] = 'password'
        self.fields['password2'].widget.attrs['type'] = 'password'

class CVUploadForm(forms.Form):
    cv_file = forms.FileField(
        label='CV File (PDF/DOCX)',
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.docx',
            'class': 'hidden'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', '')

class JobDescriptionForm(forms.Form):
    job_description = forms.CharField(
        label='Job Description',
        widget=forms.Textarea(attrs={
            'rows': '8',
            'placeholder': 'Tempel deskripsi pekerjaan lengkap di sini...',
            'class': 'field'
        })
    )