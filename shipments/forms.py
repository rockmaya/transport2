from django import forms
from .models import Shipment, FixedCostConfig
from .models import VehicleMaintenance, MONTH_CHOICES

class ShipmentForm(forms.ModelForm):
    departure_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Departure Date & Time"
    )
    arrival_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Arrival Date & Time"
    )

    class Meta:
        model = Shipment
        fields = [
            'trip_no', 'date', 'vehicle_no', 'vehicle_owner',
            'origin', 'destination', 'item', 'fuel_ltr',
            'departure_datetime', 'arrival_datetime'
        ]
        widgets = {
            'trip_no': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

# class FixedCostConfigForm(forms.ModelForm):
#     class Meta:
#         model = FixedCostConfig
#         fields = ['salary', 'insurance', 'depriciation']
#         widgets = {
#             'salary': forms.NumberInput(attrs={'class': 'form-control'}),
#             'insurance': forms.NumberInput(attrs={'class': 'form-control'}),
#             'depriciation': forms.NumberInput(attrs={'class': 'form-control'}),
#         }

from django import forms
from django.utils import timezone
from .models import FixedCostConfig

# Assuming you have MONTH_CHOICES in constants or same file

class FixedCostConfigForm(forms.ModelForm):
    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    year = forms.ChoiceField(
        choices=[(y, y) for y in range(2020, timezone.now().year + 6)],  # Auto-adjusts year range
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    class Meta:
        model = FixedCostConfig
        fields = ['month', 'year', 'salary', 'insurance', 'depriciation']
        widgets = {
            'salary': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'insurance': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'depriciation': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')

        if month and year:
            qs = FixedCostConfig.objects.filter(month=month, year=year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A fixed cost configuration already exists for {month} {year}. Please edit or delete it."
                )

        return cleaned_data








# class VehicleMaintenanceForm(forms.ModelForm):
#     vehicle_no = forms.CharField(widget=forms.TextInput(attrs={
#         'class': 'form-control form-control-sm',
#         'placeholder': 'Vehicle No'
#     }))
#     month = forms.ChoiceField(choices=MONTH_CHOICES, widget=forms.Select(attrs={
#         'class': 'form-select form-select-sm'
#     }))
#     total_cost = forms.DecimalField(widget=forms.NumberInput(attrs={
#         'class': 'form-control form-control-sm'
#     }))
#     remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={
#         'class': 'form-control form-control-sm',
#         'rows': 2
#     }))

#     class Meta:
#         model = VehicleMaintenance
#         fields = ['vehicle_no', 'month', 'total_cost', 'remarks']

# forms.py
from django import forms
from .models import VehicleMaintenance, MONTH_CHOICES

class VehicleMaintenanceForm(forms.ModelForm):
    class Meta:
        model = VehicleMaintenance
        fields = ['vehicle_no', 'month', 'year', 'total_cost', 'remarks']
        widgets = {
            'month': forms.Select(
                choices=MONTH_CHOICES, 
                attrs={'class': 'form-select form-select-sm'}
            ),
            'year': forms.Select(
                choices=[(y, y) for y in range(2020, 2031)], 
                attrs={'class': 'form-select form-select-sm'}
            ),
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'id': 'id_vehicle_no'}),
            'total_cost': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        vehicle_no = cleaned_data.get('vehicle_no')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')

        if vehicle_no and month and year:
            exists = VehicleMaintenance.objects.filter(
                vehicle_no=vehicle_no,
                month=month,
                year=year
            )
            # If editing, exclude current instance
            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError(
                    "A record for this vehicle in this month and year already exists. You can edit or delete it."
                )

        return cleaned_data



    def clean(self):
        cleaned_data = super().clean()
        vehicle = cleaned_data.get('vehicle_no')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')

        if vehicle and month and year:
            qs = VehicleMaintenance.objects.filter(vehicle_no=vehicle, month=month, year=year)
            # Exclude the instance itself when editing
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A record for {vehicle} in {month}/{year} already exists. Please edit or delete the existing record."
                )
        return cleaned_data



