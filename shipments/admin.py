from django.contrib import admin
from .models import Shipment, VariableCost, FixedCostConfig, FixedCostRecord, FixedCost
from django.http import HttpResponse
import openpyxl
from decimal import Decimal
from .models import VehicleMaintenance
from django.utils import timezone
from django.utils.timezone import is_aware




class FixedCostInline(admin.TabularInline):
    model = FixedCost
    extra = 0
    min_num = 0
    can_delete = True


class VariableCostInline(admin.StackedInline):
    model = VariableCost
    can_delete = False
    verbose_name_plural = "Variable Cost"
    extra = 0


class FixedCostRecordInline(admin.TabularInline):
    model = FixedCostRecord
    can_delete = False
    extra = 0


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'trip_no',
        'date',
        'vehicle_no',
        'vehicle_owner',
        'origin',
        'destination',
    'departure_datetime',
    'arrival_datetime',
    'trip_duration_days',
        'item_qty',
        'fuel_ltr',
        'remaining_fuel',
        'fuel_consumption',
        'fare',
        'recovery_fare',
        'fuel_tk',
        'toll',
        'food',
        'repair',
        'police',
        'without_doc',
        "maintenance_cost_field",
        'salary',
        'insurance',
        'depriciation',
        'profit_loss',
        'status',
    )
    readonly_fields = ("fuel_consumed",)

    list_filter = ('status', 'origin', 'destination', 'date')
    search_fields = ('trip_no', 'vehicle_no', 'origin', 'destination', 'item')
    inlines = [VariableCostInline, FixedCostRecordInline]
    readonly_fields = ("trip_no", "created_by")
    actions = ["export_to_excel"]

    # Item display
    def item_qty(self, obj):
        return obj.item
    item_qty.short_description = "Item"

    # Variable cost fields
    def fare(self, obj):
        return obj.variable_cost.fare if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def recovery_fare(self, obj):
        return obj.variable_cost.recovery_fare if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def fuel_tk(self, obj):
        return obj.variable_cost.fuel_tk if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def toll(self, obj):
        return obj.variable_cost.toll if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def food(self, obj):
        return obj.variable_cost.food if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def repair(self, obj):
        return obj.variable_cost.repair if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def police(self, obj):
        return obj.variable_cost.police if hasattr(obj, 'variable_cost') else Decimal('0.00')

    def without_doc(self, obj):
        return obj.variable_cost.without_doc if hasattr(obj, 'variable_cost') else Decimal('0.00')

    # Fixed cost fields
    def salary(self, obj):
        return obj.prorated_salary or Decimal('0.00')

    def insurance(self, obj):
        return obj.prorated_insurance or Decimal('0.00')

    def depriciation(self, obj):
        return obj.prorated_depriciation or Decimal('0.00')
    
    def maintenance_cost_field(self, obj):
        return obj.prorated_maintenance_cost or Decimal('0.00')
    maintenance_cost_field.short_description = "Maintenance Cost"

    # Profit / Loss
    def profit_loss(self, obj):
        total_income = self.fare(obj) + self.recovery_fare(obj)
        total_expense = (
            self.fuel_tk(obj) +
            self.toll(obj) +
            self.food(obj) +
            self.repair(obj) +
            self.police(obj) +
            self.without_doc(obj) +
            self.salary(obj) +
            self.insurance(obj) +
            self.depriciation(obj)+
            self.maintenance_cost_field(obj)  # use prorated maintenance cost

        )
        return total_income - total_expense
    profit_loss.short_description = "Profit/(Loss)"
    

    def vehicle_owner(self, obj):
        owners = { "DMT-DHA-14-0131": "SFLL", "DMT-DHA-11-0489": "SFLL", "DMT-DHA-11-0490": "SFLL", "DMT U 11-2828": "SFLL", "DMT U 11-2829": "SFLL","DMT U 11-2885": "SFLL",
    "DMT U 11-2886": "SFLL",
    "DMT U 11-1256": "SFLL",
    "DMT AU 14-1200": "SFLL",
    "DMT AU 14-1198": "SFLL",
    "DMT AU 14-1199": "SFLL",
    "NOR MA 11-0024": "SFLL",
    "NOR MA 11-0029": "SFLL",
    "DMT MA 11-2718": "SFLL",
    "DMT MA 11-2719": "SFLL",
    "DMT MA 11-2720": "SFLL",
    "DMT MA 11-2721": "SFLL",
    "DMT MA 11-2722": "SFLL",
    "DMT MA 11-2723": "SFLL",
    "DMT MA 11-2724": "SFLL",
    "DMT MA 11-2725": "SFLL",
    "DMT MA 11-2726": "SFLL",
    "DMT MA 11-2727": "SFLL",
    "DMT-MA-11-4591": "SFLL",
    "DMT-MA-11-4592": "SFLL",
    "DMT-MA-11-4593": "SFLL",
    "DMT-MA-11-4594": "SFLL",
    "DMT-MA-11-4595": "SFLL",
    "DMT-MA-11-4596": "SFLL",
    "DMT-MA-11-4597": "SFLL",
    "DMT-MA-11-4784": "SFLL",
    "DMT-MA-11-4785": "SFLL",
    "DMT-MA-11-4786": "SFLL",
    "DMT-MA-11-4787": "SFLL",
    "DMT-MA-11-4788": "SFLL",
    "DMT-MA-11-5650": "SFLL",
    "DMT-MA-11-5651": "SFLL",
    "DMT-MA-11-5652": "SFLL",
    "DMT-MA-11-5653": "SFLL",
    "DMT-MA-11-5654": "SFLL",
    "DMT-MA-11-5655": "SFLL",
    "DMT-MA-11-5656": "SFLL",
    "DMT-MA-11-5657": "SFLL",
    "DMT-MA-11-5658": "SFLL",
    "DMT-MA-11-5659": "SFLL",
    "DMT-MA-14-1232": "SFLL",
    "DMT-MA-14-1233": "SFLL",
    "DMT-MA-14-1234": "SFLL",
    "DMT-MA-14-1235": "SFLL",
    "DMT-MA-14-1236": "SFLL",
    "DMT-MA-14-1237": "SFLL",
    "DMT-MA-14-1238": "SFLL",
    "DMT-MA-14-1239": "SFLL",
    "DMT-MA-14-1240": "SFLL",
    "DMT-MA-14-1241": "SFLL",
    "DMT-MA-14-1242": "SFLL",
    "DMT-MA-14-1243": "SFLL",
    "DMT-THA-14-4348": "SFLL",
    "DMT-THA-14-4349": "SFLL",
    "DMT-THA-14-4350": "SFLL",
    "DMT-MA-13-1757": "SFLL",
    "DMT-MA-11-8207": "SFLL",
    "DMT-MA-11-8208": "SFLL",
    "DMT-MA-11-8209": "SFLL",
    "DMT-MA-11-8210": "SFLL",
    "DMT-MA-11-8211": "SFLL",
    "DMT-MA-11-8212": "SFLL",
    "DMT-MA-11-8213": "SFLL",
    "DMT-MA-11-8214": "SFLL",
    "DMT-MA-11-8215": "SFLL",
    "DMT-MA-11-8216": "SFLL",
    "DMT-DHA-14-0130": "GBFML",
    "DMT-U-14-3898": "GBFML",
    "DMT-U-14-3899": "GBFML",
    "DMT-U-14-3900": "GBFML",
    "DMT-U-14-3901": "GBFML",
    "DM-MA-11-6729": "GBFML",
    "DM-MA-11-6730": "GBFML",
    "DM-MA-11-6731": "GBFML",
    "DM-MA-11-6733": "GBFML",
    "DM-MA-11-6734": "GBFML",
    "DM-MA-11-6735": "GBFML",
    "DM-U-14-3524": "GBFML",
    "DM-U-14-3525": "GBFML",
    "DM-U-14-3526": "GBFML",
    "DM-MA-11-6430": "GBFML",
    "DM-MA-11-6431": "GBFML",
    "DM-MA-11-6432": "GBFML",
    "DM-MA-11-6437": "GBFML",
    "DM-MA-11-4944": "GBFML",
    "DMT-U-11-5474": "GBFML",
    "DMT-U-11-5475": "GBFML"}
        return owners.get(obj.vehicle_no, "unknown")
    
    vehicle_owner.short_description = "Owner"

    # Save logic
    # Save / Delete logic
    def save_model(self, request, obj, form, change):
        obj.fuel_consumption = obj.fuel_ltr - obj.remaining_fuel

        if not obj.pk:
            obj.created_by = request.user
        # if obj.status == "Posted" and not request.user.is_superuser:
        #     from django.core.exceptions import PermissionDenied
        #     raise PermissionDenied("Cannot edit a posted shipment")
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return True
        # if obj and obj.status == "Posted" and not request.user.is_superuser:
        #     return False
        # return super().has_delete_permission(request, obj)
    
    # Export to Excel action
    def export_to_excel(self, request, queryset):
        import openpyxl
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Shipments"

        # Exact columns as you specified
        headers = [
            "Trip no",
            "Date",
            "Vehicle no",
            "Vehicle owner",
            "Origin",
            "Destination",

            "Departure Date & Time",

            "Item",
            "Fuel(LTR)",
            "Remaining Fuel(LTR)",
            "Fuel Consumption(LTR)",
            "Fare",
            "Recovery fare",
            "Actual Fuel Cost",
            "Toll",
            "Food",
            "Repair",
            "Police",
            "Without doc",
            "Maintenance cost",
            "Salary",
            "Insurance",
            "Depreciation",
            "Profit/(Loss)",

            "Arrival Date & Time",
            "Trip Duration (Days)",

            "Status"
        ]
        ws.append(headers)

        for shipment in queryset:
        # for shipment in queryset:
            # handle datetime safely: remove tzinfo and format nicely
            def clean_dt(dt):
                if not dt:
                    return ""
                if is_aware(dt):
                    dt = dt.replace(tzinfo=None)  # remove timezone
                return dt.strftime("%Y-%m-%d %H:%M")  # format cleanly

            row = [
                shipment.trip_no,
                shipment.date.strftime("%Y-%m-%d") if shipment.date else "",
                shipment.vehicle_no,
                self.vehicle_owner(shipment),
                shipment.origin,
                shipment.destination,

                clean_dt(shipment.departure_datetime),

                shipment.item,
                shipment.fuel_ltr,
                shipment.remaining_fuel,
                shipment.fuel_consumption,
                self.fare(shipment),
                self.recovery_fare(shipment),
                self.fuel_tk(shipment),
                self.toll(shipment),
                self.food(shipment),
                self.repair(shipment),
                self.police(shipment),
                self.without_doc(shipment),
                self.maintenance_cost_field(shipment),
                self.salary(shipment),
                self.insurance(shipment),
                self.depriciation(shipment),
                self.profit_loss(shipment),

                clean_dt(shipment.arrival_datetime),
                shipment.trip_duration_days,

                shipment.status
            ]
            ws.append(row)

        # Auto-adjust column width
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column].width = max_length + 2

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename=shipments.xlsx'
        wb.save(response)
        return response


    export_to_excel.short_description = "Export selected shipments to Excel"



@admin.register(FixedCostConfig)
class FixedCostConfigAdmin(admin.ModelAdmin):
    #list_display = ('id', 'salary', 'insurance', 'depriciation', "created_at")
    list_display = ('month', 'year', "salary", 'insurance', 'depriciation', "created_by", "created_at", "updated_at")


@admin.register(FixedCost)
class FixedCostAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'salary', 'insurance', 'depreciation')
    list_select_related = ('shipment',)

    def salary(self, obj):
        return obj.shipment.prorated_salary
    salary.short_description = 'Salary'

    def insurance(self, obj):
        return obj.shipment.prorated_insurance
    insurance.short_description = 'Insurance'

    def depreciation(self, obj):
        return obj.shipment.prorated_depriciation
    depreciation.short_description = 'Depreciation'

    # Show only one row per shipment
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # distinct by shipment
        seen = set()
        distinct_ids = []
        for obj in qs:
            if obj.shipment_id not in seen:
                seen.add(obj.shipment_id)
                distinct_ids.append(obj.pk)
        return qs.filter(pk__in=distinct_ids)


@admin.register(VariableCost)
class VariableCostAdmin(admin.ModelAdmin):
    list_display = (
        "shipment",
        "fare",
        "recovery_fare",
        "fuel_tk",
        "toll",
        "food",
        "repair",
        "police",
        "without_doc"
    )

class ShipmentAdmin(admin.ModelAdmin):
    readonly_fields = ("created_by", "created_at")
    list_display = ("trip_number", "vehicle", "route", "created_by")


@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('vehicle_no', 'month', 'year', 'total_cost', 'remarks', 'created_by', 'created_at', "updated_at")
    list_filter = ('vehicle_no', 'month', 'year')
    search_fields = ('vehicle_no',)