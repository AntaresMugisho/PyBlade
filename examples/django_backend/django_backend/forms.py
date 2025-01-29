from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Your name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+1 234 567 8900'})
    )
    subject = forms.ChoiceField(
        choices=[
            ('general', 'General Inquiry'),
            ('support', 'Technical Support'),
            ('feedback', 'Feedback'),
        ],
        required=True
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        required=True
    )
    subscribe = forms.BooleanField(
        required=False,
        initial=True,
        label='Subscribe to newsletter'
    )
    priority = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        required=True
    )
    attachment = forms.FileField(
        required=False,
        help_text='Max file size: 5MB'
    )