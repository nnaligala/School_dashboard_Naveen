from django import forms
from django.conf import settings


class CSVImportForm(forms.Form):
    file = forms.FileField(label="CSV file")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file.")
        if f.size > settings.MAX_UPLOAD_BYTES:
            raise forms.ValidationError("File is too large.")
        try:
            return f.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise forms.ValidationError("File must be UTF-8 text.") from exc
