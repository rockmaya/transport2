from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from django.utils.timezone import localtime
from datetime import datetime, date
from datetime import datetime, date as _date
from django.utils import timezone



MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'),
    (4, 'April'), (5, 'May'), (6, 'June'),
    (7, 'July'), (8, 'August'), (9, 'September'),
    (10, 'October'), (11, 'November'), (12, 'December')
]


# Utility to convert None to Decimal
def to_decimal(val):
    return Decimal(val) if val is not None else Decimal('0.00')


class FixedCostConfig(models.Model):
    """Global fixed costs used for prorating per month/year"""
    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    year = models.PositiveIntegerField()
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    depriciation = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # fixed typo
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ('month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Fixed Cost Config - {self.get_month_display()}/{self.year}"






class Shipment(models.Model):
    trip_no = models.CharField(max_length=20, unique=True)
    date = models.DateField()
    vehicle_no = models.CharField(max_length=50)
    vehicle_owner = models.CharField(max_length=50)
    origin = models.CharField(max_length=50)
    destination = models.CharField(max_length=50)
    item = models.CharField(max_length=50)
    fuel_ltr = models.FloatField(default=0)
    remaining_fuel = models.FloatField(default=0)  # corresponds to the form field "Remaining Fuel"
    fuel_consumption = models.FloatField(default=0)  # will store Up Fuel - Remaining Fuel
    
    departure_datetime = models.DateTimeField(null=True, blank=True)
    arrival_datetime   = models.DateTimeField(null=True, blank=True)
    trip_duration_days = models.PositiveIntegerField(default=0, help_text="Duration in days (same day = 1)")



    status = models.CharField(max_length=20, default="New")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="shipments"
    )

    # Snapshot of fixed costs at creation
    salary_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    insurance_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    depriciation_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Fixed costs at posting time
    fixed_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fixed_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fixed_depriciation = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Prorated costs
    prorated_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    prorated_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    prorated_depriciation = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    prorated_maintenance_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )

    # Total cost stored in DB
    total_cost_calculated = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    # Maintenance cost (new field in DB)
    maintenance_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ["-trip_no"]

    def __str__(self):
        return f"{self.trip_no} | {self.vehicle_no} | {self.origin} → {self.destination}"


    def save(self, *args, **kwargs):
        """Auto-assign Trip No, snapshot fixed costs, and prorate costs"""
        new_instance = self.pk is None

        # Ensure self.date is a date object
        if isinstance(self.date, str):
            try:
                self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
            except ValueError:
                self.date = date.today()

        # Auto-assign trip number if new
        if new_instance and not self.trip_no:
            last_shipment = Shipment.objects.order_by("-id").first()
            if last_shipment and last_shipment.trip_no and '-' in last_shipment.trip_no:
                parts = last_shipment.trip_no.split('-')
                try:
                    last_number = int(parts[1])
                except (IndexError, ValueError):
                    last_number = 0
                self.trip_no = f"TRIP-{last_number + 1:09d}"
            else:
                self.trip_no = "TRIP-000000001"

        # Snapshot fixed costs based on shipment's month/year
        config = FixedCostConfig.objects.filter(month=self.date.month, year=self.date.year).first()
        if config:
            self.fixed_salary = config.salary
            self.fixed_insurance = config.insurance
            self.fixed_depriciation = config.depriciation
        else:
            self.fixed_salary = self.fixed_insurance = self.fixed_depriciation = Decimal('0.00')

        self.salary_snapshot = self.fixed_salary
        self.insurance_snapshot = self.fixed_insurance
        self.depriciation_snapshot = self.fixed_depriciation

        super().save(*args, **kwargs)

        # Update fuel consumption
        self.fuel_consumption = self.fuel_ltr - self.remaining_fuel
        Shipment.objects.filter(pk=self.pk).update(fuel_consumption=self.fuel_consumption)

        # --- Prorate fixed costs across all trips on the same date ---
        trips = Shipment.objects.filter(date=self.date)
        trip_count = trips.count() or 1

        if config:
            prorated_salary = (config.salary / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            prorated_insurance = (config.insurance / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            prorated_depriciation = (config.depriciation / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            prorated_salary = prorated_insurance = prorated_depriciation = Decimal('0.00')

        Shipment.objects.filter(pk__in=[t.pk for t in trips]).update(
            prorated_salary=prorated_salary,
            prorated_insurance=prorated_insurance,
            prorated_depriciation=prorated_depriciation
        )

        # --- Prorate maintenance cost per vehicle/month/year ---
        month = self.date.month
        year = self.date.year
        vehicle_trips = Shipment.objects.filter(
            vehicle_no=self.vehicle_no,
            date__month=month,
            date__year=year
        )
        vehicle_trip_count = vehicle_trips.count() or 1

        vm = VehicleMaintenance.objects.filter(vehicle_no=self.vehicle_no, month=month, year=year).first()
        if vm:
            prorated_maintenance = (vm.total_cost / vehicle_trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            prorated_maintenance = Decimal('0.00')

        Shipment.objects.filter(pk__in=[t.pk for t in vehicle_trips]).update(
            maintenance_cost=prorated_maintenance
        )

        # ---- NEW: compute trip_duration_days based on departure/arrival datetimes ----
        # We'll compute and persist the integer day-count: (arrival_date - departure_date).days + 1
        try:
            dep = self.departure_datetime
            arr = self.arrival_datetime
            if dep and arr:
                # compare dates (aware/naive handled by Django fields usually)
                dep_date = (dep.astimezone(timezone.get_current_timezone()).date()
                            if timezone.is_aware(dep) else dep.date())
                arr_date = (arr.astimezone(timezone.get_current_timezone()).date()
                            if timezone.is_aware(arr) else arr.date())

                if arr_date >= dep_date:
                    days = (arr_date - dep_date).days + 1
                else:
                    # arrival before departure (unexpected) -> fallback to 1 day
                    days = 1
            else:
                days = 0  # missing datetimes -> zero (or you can keep default)
        except Exception:
            days = 0

        if self.trip_duration_days != days:
            self.trip_duration_days = days
            # update only that field to avoid recursion
            Shipment.objects.filter(pk=self.pk).update(trip_duration_days=self.trip_duration_days)

    @property
    def total_cost(self):
        vc = getattr(self, "variable_cost", None)
        income = Decimal(vc.fare or 0) + Decimal(vc.recovery_fare or 0) if vc else Decimal('0.00')
        expenses = (
            (vc.fuel_tk if vc else 0) + (vc.toll if vc else 0) + (vc.food if vc else 0) +
            (vc.repair if vc else 0) + (vc.police if vc else 0) + (vc.without_doc if vc else 0) +
            self.prorated_salary + self.prorated_insurance + self.prorated_depriciation +
            self.maintenance_cost  # include maintenance_cost in total cost calculation if needed
        )
        return (income - Decimal(expenses)).quantize(Decimal('0.01'))



class VariableCost(models.Model):
    shipment = models.OneToOneField(
        Shipment, on_delete=models.CASCADE, related_name="variable_cost"
    )
    fare = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recovery_fare = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fuel_tk = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    toll = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    repair = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    police = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    without_doc = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Variable Cost for {self.shipment.trip_no}"


class FixedCost(models.Model):
    """Optional: per-shipment fixed costs if needed"""
    shipment = models.ForeignKey(
        Shipment,
        related_name='fixed_costs',
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=50,
        choices=[('salary','Salary'), ('insurance','Insurance'), ('depriciation','Depriciation')]
    )
    value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('shipment', 'name')


class FixedCostRecord(models.Model):
    """Optional historical record"""
    shipment = models.ForeignKey(
        Shipment,
        related_name='fixed_cost_records',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))





# class VehicleMaintenance(models.Model):
#     vehicle_no = models.CharField(max_length=50)
#     month = models.IntegerField(choices=[(i, i) for i in range(1,13)])
#     year = models.IntegerField()
#     total_cost = models.FloatField()
#     remarks = models.TextField(blank=True, null=True)
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.vehicle_no} - {self.month}/{self.year}"



class VehicleMaintenance(models.Model):
    vehicle_no = models.CharField(max_length=50)
    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    year = models.PositiveIntegerField()
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vehicle_no', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.vehicle_no} - {self.month}/{self.year} - {self.total_cost}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save or update the maintenance entry

        # Recalculate prorated maintenance cost for shipments of this vehicle/month/year
        trips = Shipment.objects.filter(
            vehicle_no=self.vehicle_no,
            date__year=self.year,
            date__month=self.month
        )
        if trips.exists():
            prorated_cost = Decimal(self.total_cost) / trips.count()
            prorated_cost = prorated_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for t in trips:
                t.prorated_maintenance_cost = prorated_cost
                t.save(update_fields=['prorated_maintenance_cost'])
