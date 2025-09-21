from django import forms
from .models import Vehicle
import re

class VehicleForm(forms.ModelForm):
    TIME_UNITS = [
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ]
    check_interval_value = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter number'}),
        label='Check Frequency'
    )
    check_interval_unit = forms.ChoiceField(
        choices=TIME_UNITS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Time Unit'
    )

    class Meta:
        model = Vehicle
        fields = ['plate_number', 'description', 'check_interval_value', 'check_interval_unit']
        widgets = {
            'plate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_plate_number(self):
        plate_number = self.cleaned_data['plate_number'].strip().upper()
        patterns = [
            (r'^T\d{3}[A-Z]{3}$', 'Private/Commercial (e.g., T123ABC)'),
            (r'^G\d{4,5}$', 'Government (e.g., G1234 or G12345)'),
            (r'^T\d{3}(TAX|BUS)$', 'Taxi/Bus (e.g., T123TAX or T123BUS)'),
            (r'^\d{3}CD\d{2}$', 'Diplomatic (e.g., 123CD45)'),
            (r'^TZ\d{4}$', 'Military (e.g., TZ1234)'),
        ]
        for pattern, description in patterns:
            if re.match(pattern, plate_number):
                return plate_number
        error_message = (
            "Plate number format is not supported. Valid Tanzanian formats are: "
            + "; ".join([desc for _, desc in patterns])
        )
        raise forms.ValidationError(error_message)

    def clean(self):
        cleaned_data = super().clean()
        value = cleaned_data.get('check_interval_value')
        unit = cleaned_data.get('check_interval_unit')

        if value and unit:
            # Define max values for each unit
            max_values = {'minutes': 60, 'hours': 24, 'days': 6}
            max_value = max_values[unit]

            if value > max_value:
                if unit == 'minutes':
                    # Convert to hours if > 60 minutes
                    hours = value // 60
                    minutes = value % 60
                    if hours > 24:
                        days = hours // 24
                        hours = hours % 24
                        if days > 6:
                            raise forms.ValidationError("Interval cannot exceed 6 days.")
                        cleaned_data['check_interval_value'] = days
                        cleaned_data['check_interval_unit'] = 'days'
                    else:
                        cleaned_data['check_interval_value'] = hours
                        cleaned_data['check_interval_unit'] = 'hours'
                elif unit == 'hours':
                    # Convert to days if > 24 hours
                    days = value // 24
                    hours = value % 24
                    if days > 6:
                        raise forms.ValidationError("Interval cannot exceed 6 days.")
                    cleaned_data['check_interval_value'] = days
                    cleaned_data['check_interval_unit'] = 'days'
                elif unit == 'days':
                    raise forms.ValidationError("Interval cannot exceed 6 days.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        value = self.cleaned_data['check_interval_value']
        unit = self.cleaned_data['check_interval_unit']
        # Convert to seconds
        if unit == 'minutes':
            instance.check_interval = value * 60
        elif unit == 'hours':
            instance.check_interval = value * 3600
        elif unit == 'days':
            instance.check_interval = value * 86400
        if commit:
            instance.save()
        return instance

class DepositForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, widget=forms.NumberInput(attrs={'class': 'form-control'}))