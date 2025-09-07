from decimal import Decimal, ROUND_HALF_UP
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Shipment, VariableCost, FixedCost, FixedCostConfig

def to_decimal(val):
    return Decimal(val) if val is not None else Decimal('0.00')


@receiver(post_save, sender=Shipment)
def create_fixed_cost_entries(sender, instance, created, **kwargs):
    """Create default fixed cost records after shipment is created"""
    if created:
        if not instance.fixed_costs.exists():  # <- updated to match related_name
            FixedCost.objects.bulk_create([
                FixedCost(shipment=instance, name='salary', value=instance.fixed_salary or Decimal('0.00')),
                FixedCost(shipment=instance, name='insurance', value=instance.fixed_insurance or Decimal('0.00')),
                FixedCost(shipment=instance, name='depriciation', value=instance.fixed_depriciation or Decimal('0.00')),
            ])


def calculate_shipment_cost(sender, instance, **kwargs):
    """Calculate prorated costs and total cost"""
    shipment = getattr(instance, 'shipment', instance)  # works for Shipment or VariableCost
    if not shipment:
        return
    if getattr(shipment, "_cost_calculated", False):
        return

    # Fetch fixed costs using correct related_name
    fixed_records = {fc.name: fc.value for fc in shipment.fixed_costs.all()}

    fixed_config = FixedCostConfig.objects.first()

    salary = fixed_records.get("salary") or (Decimal(fixed_config.salary) if fixed_config else Decimal('0.00'))
    insurance = fixed_records.get("insurance") or (Decimal(fixed_config.insurance) if fixed_config else Decimal('0.00'))
    depriciation = fixed_records.get("depriciation") or (Decimal(fixed_config.depriciation) if fixed_config else Decimal('0.00'))

    trips = Shipment.objects.filter(date=shipment.date)
    trip_count = Decimal(trips.count() or 1)

    prorated_salary = (salary / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    prorated_insurance = (insurance / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    prorated_depriciation = (depriciation / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    for trip in trips:
        trip.prorated_salary = prorated_salary
        trip.prorated_insurance = prorated_insurance
        trip.prorated_depriciation = prorated_depriciation

        vc = getattr(trip, "variable_cost", None)
        fare = to_decimal(vc.fare) if vc else Decimal('0.00')
        recovery = to_decimal(vc.recovery_fare) if vc else Decimal('0.00')
        fuel_tk = to_decimal(vc.fuel_tk) if vc else Decimal('0.00')
        toll = to_decimal(vc.toll) if vc else Decimal('0.00')
        food = to_decimal(vc.food) if vc else Decimal('0.00')
        repair = to_decimal(vc.repair) if vc else Decimal('0.00')
        police = to_decimal(vc.police) if vc else Decimal('0.00')
        without_doc = to_decimal(vc.without_doc) if vc else Decimal('0.00')

        total_cost = (fare + recovery - fuel_tk - toll - food - repair - police - without_doc
                      - prorated_salary - prorated_insurance - prorated_depriciation)
        trip.total_cost_calculated = total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        trip._cost_calculated = True
        trip.save(update_fields=[
            "prorated_salary", "prorated_insurance", "prorated_depriciation", "total_cost_calculated"
        ])


# shipments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, ROUND_HALF_UP
from .models import Shipment, VehicleMaintenance

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Shipment, VehicleMaintenance

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Shipment, VehicleMaintenance

@receiver(post_save, sender=Shipment)
def calculate_maintenance_cost(sender, instance, created, **kwargs):
    """
    Calculate and store maintenance cost for a shipment after it is saved.
    """

    # Ensure instance.date is a date object
    if isinstance(instance.date, str):
        instance_date = datetime.strptime(instance.date, "%Y-%m-%d").date()
    else:
        instance_date = instance.date

    month = instance_date.month
    year = instance_date.year  # integer, safe

    # Fetch VehicleMaintenance for this vehicle, month, and year
    vm = VehicleMaintenance.objects.filter(
        vehicle_no=instance.vehicle_no,
        month=month,
        year=year,
    ).first()

    if vm:
        # Count all trips for this vehicle in this month/year including this one
        total_trips = Shipment.objects.filter(
            vehicle_no=instance.vehicle_no,
            date__year=year,
            date__month=month
        ).count() or 1

        maintenance_cost = (Decimal(vm.total_cost) / total_trips).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        maintenance_cost = Decimal('0.00')

    # Update the shipment without triggering recursion
    Shipment.objects.filter(pk=instance.pk).update(maintenance_cost=maintenance_cost)


@receiver(post_save, sender=VehicleMaintenance)
def update_prorated_cost(sender, instance, **kwargs):
    trips = Shipment.objects.filter(
        vehicle_no=instance.vehicle_no,
        date__year=instance.year,
        date__month=instance.month
    )
    if trips.exists():
        prorated_cost = Decimal(instance.total_cost) / trips.count()
        prorated_cost = prorated_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        for t in trips:
            t.prorated_maintenance_cost = prorated_cost
            t.save(update_fields=['prorated_maintenance_cost'])


@receiver(post_save, sender=Shipment)
def calculate_shipment_profit_loss(sender, instance, created, **kwargs):
    """
    Calculate total profit/loss for a shipment and store in DB.
    Matches frontend calculation.
    """
    shipment = instance

    # Variable costs
    vc = getattr(shipment, "variable_cost", None)
    fare = Decimal(vc.fare) if vc else Decimal('0.00')
    recovery = Decimal(vc.recovery_fare) if vc else Decimal('0.00')
    fuel_tk = Decimal(vc.fuel_tk) if vc else Decimal('0.00')
    toll = Decimal(vc.toll) if vc else Decimal('0.00')
    food = Decimal(vc.food) if vc else Decimal('0.00')
    repair = Decimal(vc.repair) if vc else Decimal('0.00')
    police = Decimal(vc.police) if vc else Decimal('0.00')
    without_doc = Decimal(vc.without_doc) if vc else Decimal('0.00')

    # Fixed costs
    salary = shipment.prorated_salary or Decimal('0.00')
    insurance = shipment.prorated_insurance or Decimal('0.00')
    depriciation = shipment.prorated_depriciation or Decimal('0.00')

    # Maintenance cost
    maintenance = shipment.maintenance_cost or Decimal('0.00')

    total_expense = fuel_tk + toll + food + repair + police + without_doc + salary + insurance + depriciation + maintenance
    total_income = fare + recovery

    profit_loss = (total_income - total_expense).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Save into total_cost_calculated field
    Shipment.objects.filter(pk=shipment.pk).update(total_cost_calculated=profit_loss)
