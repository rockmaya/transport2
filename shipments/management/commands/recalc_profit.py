from decimal import Decimal
from django.core.management.base import BaseCommand
from shipments.models import Shipment

class Command(BaseCommand):
    help = "Recalculate profit/loss for all shipments"

    def handle(self, *args, **kwargs):
        updated_count = 0
        for shipment in Shipment.objects.all():
            fare = shipment.variable_cost.fare if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            recovery_fare = shipment.variable_cost.recovery_fare if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            fuel_tk = shipment.variable_cost.fuel_tk if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            toll = shipment.variable_cost.toll if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            food = shipment.variable_cost.food if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            repair = shipment.variable_cost.repair if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            police = shipment.variable_cost.police if hasattr(shipment, 'variable_cost') else Decimal('0.00')
            without_doc = shipment.variable_cost.without_doc if hasattr(shipment, 'variable_cost') else Decimal('0.00')

            salary = shipment.prorated_salary or Decimal('0.00')
            insurance = shipment.prorated_insurance or Decimal('0.00')
            depriciation = shipment.prorated_depriciation or Decimal('0.00')
            maintenance = getattr(shipment, 'maintenance_cost', Decimal('0.00'))

            profit_loss = (fare + recovery_fare) - (fuel_tk + toll + food + repair + police + without_doc + salary + insurance + depriciation + maintenance)
            
            shipment.profit_loss = profit_loss
            shipment.save(update_fields=['profit_loss'])
            updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Updated profit/loss for {updated_count} shipments"))
