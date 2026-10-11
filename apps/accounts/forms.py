from django.contrib.auth.forms import AuthenticationForm


class EmailLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email address"
        self.fields["username"].widget.attrs.update({"autocomplete": "email", "autofocus": True})
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-control"
