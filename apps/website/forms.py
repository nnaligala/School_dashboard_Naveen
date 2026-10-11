from django import forms

from .models import Enquiry


class EnquiryForm(forms.ModelForm):
    # Honeypot: real users never see or fill this field.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Enquiry
        fields = ["name", "email", "phone", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            f.widget.attrs["class"] = "form-control" if name != "website" else "hp-field"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
