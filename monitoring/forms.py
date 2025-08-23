from django import forms
from .models import Vehicle
import re

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['plate_number', 'make', 'model', 'year', 'description']
        widgets = {
            'plate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_plate_number(self):
        plate_number = self.cleaned_data['plate_number'].strip().upper()
        # Define valid Tanzanian plate number patterns
        patterns = [
            (r'^T\d{3}[A-Z]{3}$', 'Private/Commercial (e.g., T123ABC)'),  # T123ABC
            (r'^G\d{4,5}$', 'Government (e.g., G1234 or G12345)'),       # G1234 or G12345
            (r'^T\d{3}(TAX|BUS)$', 'Taxi/Bus (e.g., T123TAX or T123BUS)'), # T123TAX or T123BUS
            (r'^\d{3}CD\d{2}$', 'Diplomatic (e.g., 123CD45)'),           # 123CD45
            (r'^TZ\d{4}$', 'Military (e.g., TZ1234)'),                   # TZ1234
        ]
        for pattern, description in patterns:
            if re.match(pattern, plate_number):
                return plate_number
        # If no pattern matches, raise validation error with supported formats
        error_message = (
            "Plate number format is not supported. Valid Tanzanian formats are: "
            + "; ".join([desc for _, desc in patterns])
        )
        raise forms.ValidationError(error_message)

class DepositForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, widget=forms.NumberInput(attrs={'class': 'form-control'}))