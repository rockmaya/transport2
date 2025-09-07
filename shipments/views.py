import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Shipment
from .models import Shipment, VariableCost, FixedCostConfig
from django.http import JsonResponse
from django.http import HttpResponse
from decimal import Decimal
from .models import FixedCostConfig, FixedCostRecord
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from .models import Shipment, VariableCost, FixedCostConfig, FixedCostRecord
from django.db.models import Count
from django.contrib import messages
from datetime import date
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from django.http import HttpResponse
from django.db.models import Q
import traceback
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from .forms import FixedCostConfigForm
from django.contrib.auth.models import Group
from django.db.models import Sum, F, Count, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from collections import defaultdict, Counter
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render




global_vehicles = [
  "DMT-DHA-14-0130","DMT-DHA-14-0131","DMT-DHA-11-0489","DMT-DHA-11-0490",
  "DMT U 11-2828","DMT U 11-2829","DMT U 11-2885","DMT U 11-2886",
  "DMT U 11-1256","DMT AU 14-1200","DMT AU 14-1198","DMT AU 14-1199",
  "NOR MA 11-0024","NOR MA 11-0029","DMT MA 11-2718","DMT MA 11-2719",
  "DMT MA 11-2720","DMT MA 11-2721","DMT MA 11-2722","DMT MA 11-2723",
  "DMT MA 11-2724","DMT MA 11-2725","DMT MA 11-2726","DMT MA 11-2727",
  "DMT-MA-11-4591","DMT-MA-11-4592","DMT-MA-11-4593","DMT-MA-11-4594",
  "DMT-MA-11-4595","DMT-MA-11-4596","DMT-MA-11-4597","DMT-MA-11-4784",
  "DMT-MA-11-4785","DMT-MA-11-4786","DMT-MA-11-4787","DMT-MA-11-4788",
  "DMT-MA-11-5650","DMT-MA-11-5651","DMT-MA-11-5652","DMT-MA-11-5653",
  "DMT-MA-11-5654","DMT-MA-11-5655","DMT-MA-11-5656","DMT-MA-11-5657",
  "DMT-MA-11-5658","DMT-MA-11-5659","DMT-MA-14-1232","DMT-MA-14-1233",
  "DMT-MA-14-1234","DMT-MA-14-1235","DMT-MA-14-1236","DMT-MA-14-1237",
  "DMT-MA-14-1238","DMT-MA-14-1239","DMT-MA-14-1240","DMT-MA-14-1241",
  "DMT-MA-14-1242","DMT-MA-14-1243","DMT-THA-14-4348","DMT-THA-14-4349",
  "DMT-THA-14-4350","DMT-MA-13-1757","DMT-MA-11-8207","DMT-MA-11-8208",
  "DMT-MA-11-8209","DMT-MA-11-8210","DMT-MA-11-8211","DMT-MA-11-8212",
  "DMT-MA-11-8213","DMT-MA-11-8214","DMT-MA-11-8215","DMT-MA-11-8216",
  "DMT-U-14-3898","DMT-U-14-3899","DMT-U-14-3900","DMT-U-14-3901",
  "DM-MA-11-6729","DM-MA-11-6730","DM-MA-11-6731","DM-MA-11-6733",
  "DM-MA-11-6734","DM-MA-11-6735","DM-U-14-3524","DM-U-14-3525",
  "DM-U-14-3526","DM-MA-11-6430","DM-MA-11-6431","DM-MA-11-6432",
  "DM-MA-11-6437","DM-MA-11-4944","DMT-U-11-5474","DMT-U-11-5475"
];


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/shipments/list/")  # ✅ go to form page after login
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")  # Redirect to login page after logout


@login_required
def change_password(request):
    if request.method == "POST":
        user = request.user
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if not new_password:
            messages.error(request, "New password cannot be empty.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # ✅ Update password
        user.set_password(new_password)
        user.save()

        # ✅ Force logout
        logout(request)

        # messages.success(request, "Password changed successfully. Please log in again.")
        return redirect("login")

    return redirect("/")


@login_required
def shipment_form(request, shipment_id=None):
    """
    Handle both creating a new shipment or updating an existing one.
    Calculates prorated fixed costs, saves variable costs, and handles posting.
    """
    # -------------------------------
    # Fetch or initialize shipment
    # -------------------------------
    shipment = get_object_or_404(Shipment, id=shipment_id) if shipment_id else Shipment()
    fixed_cost_config = FixedCostConfig.objects.first()  # global fixed cost fallback

    # -------------------------------
    # Determine next trip number
    # -------------------------------
    if not shipment.id:
        last_shipment = Shipment.objects.order_by('-id').first()
        next_trip_no = "TRIP-000000001"
        if last_shipment and last_shipment.trip_no and '-' in last_shipment.trip_no:
            try:
                parts = last_shipment.trip_no.split('-')
                last_number = int(parts[1])
                next_trip_no = f"TRIP-{last_number + 1:09d}"
            except (IndexError, ValueError):
                pass
        shipment.trip_no = next_trip_no
    else:
        next_trip_no = shipment.trip_no

    vehicles = [
  "DMT-DHA-14-0130","DMT-DHA-14-0131","DMT-DHA-11-0489","DMT-DHA-11-0490",
  "DMT U 11-2828","DMT U 11-2829","DMT U 11-2885","DMT U 11-2886",
  "DMT U 11-1256","DMT AU 14-1200","DMT AU 14-1198","DMT AU 14-1199",
  "NOR MA 11-0024","NOR MA 11-0029","DMT MA 11-2718","DMT MA 11-2719",
  "DMT MA 11-2720","DMT MA 11-2721","DMT MA 11-2722","DMT MA 11-2723",
  "DMT MA 11-2724","DMT MA 11-2725","DMT MA 11-2726","DMT MA 11-2727",
  "DMT-MA-11-4591","DMT-MA-11-4592","DMT-MA-11-4593","DMT-MA-11-4594",
  "DMT-MA-11-4595","DMT-MA-11-4596","DMT-MA-11-4597","DMT-MA-11-4784",
  "DMT-MA-11-4785","DMT-MA-11-4786","DMT-MA-11-4787","DMT-MA-11-4788",
  "DMT-MA-11-5650","DMT-MA-11-5651","DMT-MA-11-5652","DMT-MA-11-5653",
  "DMT-MA-11-5654","DMT-MA-11-5655","DMT-MA-11-5656","DMT-MA-11-5657",
  "DMT-MA-11-5658","DMT-MA-11-5659","DMT-MA-14-1232","DMT-MA-14-1233",
  "DMT-MA-14-1234","DMT-MA-14-1235","DMT-MA-14-1236","DMT-MA-14-1237",
  "DMT-MA-14-1238","DMT-MA-14-1239","DMT-MA-14-1240","DMT-MA-14-1241",
  "DMT-MA-14-1242","DMT-MA-14-1243","DMT-THA-14-4348","DMT-THA-14-4349",
  "DMT-THA-14-4350","DMT-MA-13-1757","DMT-MA-11-8207","DMT-MA-11-8208",
  "DMT-MA-11-8209","DMT-MA-11-8210","DMT-MA-11-8211","DMT-MA-11-8212",
  "DMT-MA-11-8213","DMT-MA-11-8214","DMT-MA-11-8215","DMT-MA-11-8216",
  "DMT-U-14-3898","DMT-U-14-3899","DMT-U-14-3900","DMT-U-14-3901",
  "DM-MA-11-6729","DM-MA-11-6730","DM-MA-11-6731","DM-MA-11-6733",
  "DM-MA-11-6734","DM-MA-11-6735","DM-U-14-3524","DM-U-14-3525",
  "DM-U-14-3526","DM-MA-11-6430","DM-MA-11-6431","DM-MA-11-6432",
  "DM-MA-11-6437","DM-MA-11-4944","DMT-U-11-5474","DMT-U-11-5475"
];
    
    origins = ["SFLL","DEPOT/BOGURA","GBFML-1","GBFML-2","GBFML-3"]

    destinations = ["Abhoynagar","Adamdighi","Aditmari","Agailjhara","Akhaura","Akkelpur","Alamdanga",
                    "Alfadanga","Alikadam","Amtali","Anwara","Araihazar","Ashuganj","Assasuni","Atghoria","Atpara","Atrai","Atwari","Austagram","Azmiriganj","B.Baria-S","Babuganj","Badalgachi","Badarganj","Bagatipara","Bagerhat-S","Bagha","Baghaichari","Bagherpara","Bagmara","Bahubal","Bajitpur","Bakerganj","Bakshiganj","Balaganj","Baliadangi","Baliakandi","Bamna","Banaripara","Bancharampur","Bandar","Bandarban-S","Baniachong","Banskhali","Baraigram","Barguna-S","Barhatta","Barishal-S","Barkal","Barlekha","Barura","Basail","Batiaghata","Bauphal","Beanibazar","Begumganj","Belabo","Belaichari","Belkuchi","Bera","Betagi","Bhairab","Bhaluka","Bhandaria","Bhanga","Bhangura","Bhedarganj","Bheramara","Bholahat","Bhola-S","Bhuapur","Bhurungamari","Bijoynagar","Birampur","Birganj","Birol","Biswamvarpur","Biswanath","Boalkhali","Boalmari","Bochaganj","Boda","Bogura-S","Borhanuddin","Brahmanpara","Burichong","Chakoria","Chandanish","Chandina","Chandpur-S","Charbhadrasan","Charfassion","Charghat","Chatak","Chatkhil","Chatmohar","Chhagalniya","Chilmari","Chirirbandar","Chitalmari","Chouddagram","Chowgacha","Chowhali","Chuadanga-S","Chunarughat","Companiganj","Companiganj","Cox'S,Bazar-S","Cumilla-S","Cumilla-S,Daksin","Dacope","Daganbhuiyan","Dakhin,Sunamganj","Dakshin,Surma","Damuddya","Damurhuda","Dashmina","Daudkandi","Daulatkhan","Daulatpur","Daulatpur","Debhata","Debidwar","Debiganj","Delduar","Derai","Dewanganj","Dhamoirhat","Dhamrai","Dhanbari","Dharmapasha","Dhobaura","Dhunot","Dhupchancia","Dighalia","Dighinala","Dimla","Dinajpur-S","Doarabazar","Dohar","Domar","Dumki","Dumuria","Durgapur","Durgapur","Fakirhat","Faridganj","Faridpur","Faridpur-S","Fatikchari","Fenchuganj","Feni-S","Fulbari","Fulbari","Fulbaria","Fulchari","Fulgazi","Gabtali","Gaffargaon","Gaibandha-S","Galachipa","Gangachara","Gangni","Gazaria","Gazipur-S","Ghatail","Ghior","Ghoraghat","Goalanda","Gobindaganj","Godagari","Golapganj","Gomostapur","Gopalganj-S","Gopalpur","Goshairhat","Gouranadi","Gouripur","Gowainghat","Guimara","Gurudaspur","Habiganj-S","Haimchar","Hakimpur","Haluaghat","Harinakunda","Haripur","Harirampur","Hathazari","Hatibandha","Hatiya","Haziganj","Hizla","Homna","Hossainpur","Ishwardi","Ishwarganj","Islampur","Itna","Jagannathpur","Jaldhaka","Jamalganj","Jamalpur-S","Janjira","Jashore-S","Jhalokathi-S","Jhenaidah-S","Jhenaigati","Jhikargacha","Jibannagar","Jointiapur","Joypurhat-S","Juraichari","Juri","Kabir,Hat","Kachua","Kachua","Kahaloo","Kaharol","Kalai","Kalapara","Kalaroa","Kalia","Kaliakoir","Kaliganj","Kaliganj","Kaliganj","Kaliganj","Kalihati","Kalkini","Kalmakanda","Kalukhali","Kamalganj","Kamarkhand","Kanaighat","Kapasia","Kaptai","Karimganj","Karnaphuli","Kasba","Kasiani","Kathalia","Katiadi","Kaukhali","Kaunia","Kawkhali","Kazipur","Kendua","Keraniganj","Keshabpur","Khagrachari-S","Khaliajuri","Khanshama","Khetlal","Khoksha","Kishoreganj","Kishoreganj-S","Koira","Komol,Nagar","Kotchandpur","Kotwalipara","Kulaura","Kuliarchar","Kumarkhali","Kurigram-S","Kushtia-S","Kutubdia","Lakhai","Laksham","Lalmai","Lalmohan","Lalmonirhat-S","Lalpur","Lama","Langadu","Lauhajong","Laxmichari","Laxmipur-S","Lohagara","Lohagara","Madan","Madarganj","Madaripur-S","Madhabpur","Madhukhali","Madhupur","Magura-S","Mahalchari","Manda","Manikchari","Manikganj-S","Matiranga","Matlab,(Dakshin)","Matlab,(Uttar)","Meghna","Mehendiganj","Meherpur-S","Melendah","Mirjaganj","Mirpur","Mirsharai","Mirzapur","Mithamoin","Mithapukur","Mohadevpur","Mohammadpur","Mohanganj","Mohanpur","Moheshpur","Moheskhali","Mollahat","Mongla","Monirampur","Monohardi","Monohorganj","Monpura","Morrelganj","Mothbaria","Moulvibazar-S","Mujib,Nagar","Muksudpur","Muktagacha","Muladi","Munshiganj-S","Muradnagar","Mymensingh-S","Nabiganj","Nabinagar","Nachol","Nagarkanda","Nagarpur","Nageswari","Naikhyongchari","Nakla","Nalchity","Naldanga","Nalitabari","Nandail","Nandigram","Nangalkot","Nanniarchar","Naogaon-S","Narail-S","Narayanganj-S","Naria","Narshingdi-S","Nasirnagar","Natore-S","Nawabganj","Nawabganj","Nawabganj-S","Nazirpur","Nesarabad","Netrakona-S","Niamatpur","Nikli","Nilphamari-S","Noakhali-S","Osmaninagar","Paba","Pabna-S","Paikgacha","Pakundia","Palash","Palashbari","Panchagarh-S","Panchari","Panchbibi","Pangsha","Parbatipur","Patgram","Patharghata","Patiya","Patnitala","Patuakhali-S","Pekua","Phulpur","Phultala","Pirgacha","Pirganj","Pirganj","Pirojpur-S","Porsha","Porshuram","Purbadhala","Puthia","Raiganj","Raipur","Raipura","Rajapur","Rajarhat","Rajbari-S","Rajibpur","Rajnagar","Rajoir","Rajosthali","Ramganj","Ramgarh","Ramgati","Rampal","Ramu","Rangabali","Rangamati-S","Rangpur-S","Rangunia","Raninagar","Ranisankail","Raojan","Rowangchari","Rowmari","Ruma","Rupganj","Rupsa","Sadarpur","Sadullapur","Saghata","Salikha","Saltha","Sandwip","Santhia","Sarail","Sariakandi","Sarishabari","Sarsha","Satkania","Satkhira-S","Saturia","Savar","Sayedpur","Sayestaganj","Senbag","Shahrasti","Shahzadpur","Shailkupa","Shajahanpur","Shakhipur","Shapahar","Sharankhola","Shariatpur-S","Sherpur","Sherpur-S","Shibchar","Shibganj","Shibganj","Shibpur","Shivalaya","Shyamnagar","Singair","Singra","Sirajdikhan","Sirajganj-S","Sitakunda","Sonagazi","Sonaimuri","Sonargaon","Sonatala","Sreebordi","Sreemangal","Sreenagar","Sreepur","Sreepur","Subarna,Char","Sujanagar","Sulla","Sunamganj-S","Sundarganj","Sylhet-S","Tahirpur","Tala","Taltali","Tangail-S","Tanore","Taraganj","Tarail","Tarakanda","Tarash","Teknaf","Terokhada","Tetulia","Thakurgaon-S","Thanchi","Titas","Tongibari","Trishal","Tungipara","Ukhiya","Ulipur","Ullapara","Uzirpur","Zakiganj","Zianagar"]
    
    items = ["PLY", "MDF", "MELAMINE", "WOODTEX", "JUTEXT", "HPL"]

    vehicle_owner = { "DMT-DHA-14-0131": "SFLL", "DMT-DHA-11-0489": "SFLL", "DMT-DHA-11-0490": "SFLL", "DMT U 11-2828": "SFLL", "DMT U 11-2829": "SFLL","DMT U 11-2885": "SFLL",
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



  # -------------------------------
    # Handle POST request
    # -------------------------------
    if request.method == "POST":
        action = request.POST.get("action")  # 'save' or 'post'

        # --- Shipment fields ---
        shipment.date = request.POST.get("date")
        shipment.vehicle_no = request.POST.get("vehicle_no")
        shipment.vehicle_owner = vehicle_owner.get(shipment.vehicle_no, "")
        shipment.origin = request.POST.get("origin")
        shipment.destination = request.POST.get("destination")
        shipment.item = request.POST.get("item")
        shipment.fuel_ltr = Decimal(request.POST.get("fuel_ltr") or 0)
        shipment.remaining_fuel = Decimal(request.POST.get("remaining_fuel") or 0)

        # --- New: Departure & Arrival Datetime ---
        from datetime import datetime

        dep_str = request.POST.get("departure_datetime")
        arr_str = request.POST.get("arrival_datetime")

        shipment.departure_datetime = datetime.fromisoformat(dep_str) if dep_str else None
        shipment.arrival_datetime = datetime.fromisoformat(arr_str) if arr_str else None

        # --- Calculate Trip Duration in days ---
        if shipment.departure_datetime and shipment.arrival_datetime:
            delta = shipment.arrival_datetime.date() - shipment.departure_datetime.date()
            shipment.trip_duration_days = delta.days + 1  # same-day = 1 day
        else:
            shipment.trip_duration_days = 0


        if not shipment.id:
            shipment.created_by = request.user
        shipment.status = "New" if action == "save" else "Posted"

        # --- Prorated fixed costs ---
        if (not shipment.id or shipment.prorated_salary is None) and fixed_cost_config:
            trip_count = Shipment.objects.filter(date=shipment.date).count() + (0 if shipment.id else 1)
            shipment.prorated_salary = Decimal(fixed_cost_config.salary) / trip_count
            shipment.prorated_insurance = Decimal(fixed_cost_config.insurance) / trip_count
            shipment.prorated_depriciation = Decimal(fixed_cost_config.depriciation) / trip_count

        # Save shipment to assign ID
        try:
            shipment.save()
        except RecursionError:
            traceback.print_stack(limit=10)
            raise

        # --- Variable Costs ---
        vc, _ = VariableCost.objects.get_or_create(shipment=shipment)
        vc.fare = Decimal(request.POST.get("fare") or 0)
        vc.recovery_fare = Decimal(request.POST.get("recovery_fare") or 0)
        vc.fuel_tk = Decimal(request.POST.get("fuel_tk") or 0)
        vc.toll = Decimal(request.POST.get("toll") or 0)
        vc.food = Decimal(request.POST.get("food") or 0)
        vc.repair = Decimal(request.POST.get("repair") or 0)
        vc.police = Decimal(request.POST.get("police") or 0)
        vc.without_doc = Decimal(request.POST.get("without_doc") or 0)
        vc.save()

        # --- Fixed Cost Records (snapshot) for posted shipments ---
        if action == "post" and fixed_cost_config:
            shipment.fixed_costs.all().delete()
            FixedCostRecord.objects.bulk_create([
                FixedCostRecord(shipment=shipment, name="salary", value=fixed_cost_config.salary),
                FixedCostRecord(shipment=shipment, name="insurance", value=fixed_cost_config.insurance),
                FixedCostRecord(shipment=shipment, name="depriciation", value=fixed_cost_config.depriciation),
            ])

        messages.success(request, f"Shipment saved successfully! Total Cost: {shipment.total_cost}")
        return redirect("shipment_list")

    # -------------------------------
    # Handle GET request
    # -------------------------------
    vc = None
    if shipment.id:
        try:
            vc_obj = shipment.variable_cost
            vc = {
                "fare": vc_obj.fare,
                "recovery_fare": vc_obj.recovery_fare,
                "fuel_tk": vc_obj.fuel_tk,
                "toll": vc_obj.toll,
                "food": vc_obj.food,
                "repair": vc_obj.repair,
                "police": vc_obj.police,
                "without_doc": vc_obj.without_doc,
            }
        except VariableCost.DoesNotExist:
            vc = None

    fixed_records = {fc.name: fc.value for fc in shipment.fixed_costs.all()} if shipment.id else {}
    salary = Decimal(fixed_records.get("salary", fixed_cost_config.salary if fixed_cost_config else 0))
    insurance = Decimal(fixed_records.get("insurance", fixed_cost_config.insurance if fixed_cost_config else 0))
    depriciation = Decimal(fixed_records.get("depriciation", fixed_cost_config.depriciation if fixed_cost_config else 0))

    context = {
        "shipment": shipment,
        "next_trip_no": next_trip_no,
        "vehicles": vehicles,
        "vehicle_owner": vehicle_owner,
        "from_locations": origins,
        "to_locations": destinations,
        "items": items,
        "fixed_cost": fixed_cost_config,
        "variable_cost": vc,
        "total_cost": shipment.total_cost,
    }

    return render(request, "shipments/shipment_form.html", context)

   
MONTH_NAME_TO_NUMBER = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}


@login_required
def shipment_list(request):
    # --- Get filters from GET params ---
    trip_no_query = request.GET.get("trip_no", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")
    vehicle_no = request.GET.get("vehicle_no", "")
    vehicle_owner = request.GET.get("vehicle_owner", "")
    status_query = request.GET.get("status", "")

    # --- Base queryset ---
    shipments = Shipment.objects.all().select_related("variable_cost")

    # --- Apply filters ---
    if trip_no_query:
        shipments = shipments.filter(trip_no__icontains=trip_no_query)
    if vehicle_no:
        shipments = shipments.filter(vehicle_no__icontains=vehicle_no)
    if vehicle_owner:
        shipments = shipments.filter(vehicle_owner__icontains=vehicle_owner)
    if status_query:
        shipments = shipments.filter(status=status_query)
    if from_date and to_date:
        shipments = shipments.filter(date__range=[from_date, to_date])
    elif from_date:
        shipments = shipments.filter(date__gte=from_date)
    elif to_date:
        shipments = shipments.filter(date__lte=to_date)

    # --- Annotate shipments with prorated maintenance cost ---
    for s in shipments:
        # Convert month name to number
        month_number = s.date.month

        maintenance = VehicleMaintenance.objects.filter(
            vehicle_no=s.vehicle_no,
            month=month_number,
            year=s.date.year
        ).first()

        if maintenance:
            # Count all trips of this vehicle in that month/year
            total_trips = Shipment.objects.filter(
                vehicle_no=s.vehicle_no,
                date__year=s.date.year,
                date__month=month_number
            ).count()
            # Prorated cost
            s._maintenance_cost = maintenance.total_cost / total_trips if total_trips else 0
        else:
            s._maintenance_cost = 0

    context = {
        "shipments": shipments,
        "trip_no_query": trip_no_query,
        "from_date": from_date,
        "to_date": to_date,
        "vehicle_no": vehicle_no,
        "vehicle_owner": vehicle_owner,
        "status_query": status_query,
    }
    return render(request, "shipments/shipment_list.html", context)






@login_required
def shipment_finalize(request, shipment_id):
    shipment = get_object_or_404(Shipment, id=shipment_id)
    action = request.POST.get("action")

    if action == "post":
        shipment.status = "Posted"
        shipment.save()

    return redirect("shipment_list")





@login_required
def shipment_view(request, shipment_id):
    shipment = Shipment.objects.get(id=shipment_id)
    trip_count = Shipment.objects.filter(date=shipment.date).count() or 1

    fixed_cost_config = FixedCostConfig.objects.first()

    fixed_records_qs = shipment.fixed_costs.all()
    fixed_records = {fc.name: fc.value for fc in fixed_records_qs}

    shipment.fixed_cost_total = (
    shipment.prorated_salary +
    shipment.prorated_insurance +
    sum(fc.value for fc in shipment.fixed_costs.all() if fc.name not in ["salary", "insurance"])
)

    # Prorated salary
    salary = fixed_records.get("salary") or (fixed_cost_config.salary if fixed_cost_config else 0)
    shipment.prorated_salary = Decimal(salary) / trip_count

    # Prorated insurance
    insurance = fixed_records.get("insurance") or (fixed_cost_config.insurance if fixed_cost_config else 0)
    shipment.prorated_insurance = Decimal(insurance) / trip_count

    # Prorated depriciation
    depriciation = fixed_records.get("depriciation") or (fixed_cost_config.depriciation if fixed_cost_config else 0)
    shipment.prorated_depriciation = Decimal(depriciation) / trip_count
    
    context = {
        "shipment": shipment
    }
    return render(request, "shipments/shipment_view.html", context)

@login_required
def shipment_trip_suggestions(request):
    term = request.GET.get("term", "")
    suggestions = list(
        Shipment.objects.filter(trip_no__icontains=term)
        .values_list("trip_no", flat=True)[:10]
    )
    return JsonResponse(suggestions, safe=False)

@login_required
def shipment_vehicle_suggestions(request):
    term = request.GET.get("term", "").strip()
    # Only search when term is not empty
    if term:
        vehicles = Shipment.objects.filter(vehicle_no__icontains=term).values_list("vehicle_no", flat=True).distinct()
    else:
        # If term is empty, return empty list (so nothing shows until user types)
        vehicles = []

    return JsonResponse(list(vehicles), safe=False)


def format_date(dt):
    if dt:
        return dt.strftime("%b. %d, %Y, %I:%M %p").replace(" 0", " ")
    return ""


@login_required
def shipment_export(request):
    import csv
    from decimal import Decimal
    from django.http import HttpResponse

    shipments = Shipment.objects.all().order_by("-trip_no")
    trip_no_query = request.GET.get("trip_no", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")
    vehicle_no = request.GET.get("vehicle_no", "")
    vehicle_owner = request.GET.get("vehicle_owner", "")
    status_query = request.GET.get("status", "")

    if trip_no_query:
        shipments = shipments.filter(trip_no__icontains=trip_no_query)
    if vehicle_no:
        shipments = shipments.filter(vehicle_no__icontains=vehicle_no)
    if vehicle_owner:
        shipments = shipments.filter(vehicle_owner__icontains=vehicle_owner)
    if status_query:
        shipments = shipments.filter(status=status_query)
    if from_date and to_date:
        shipments = shipments.filter(date__range=[from_date, to_date])
    elif from_date:
        shipments = shipments.filter(date__gte=from_date)
    elif to_date:
        shipments = shipments.filter(date__lte=to_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="shipments.csv"'
    writer = csv.writer(response)

    # Header row
    writer.writerow([
        "Trip No", "Date", "Vehicle No", "Vehicle Owner", "Origin", "Destination",
        "Item", "Up Fuel (Ltr)", "Remaining Fuel (Ltr)", "Fuel Consumption (Ltr)",
        "Fare", "Recovery Fare", "Actual Fuel Cost", "Toll", "Food",
        "Repair", "Police", "Without Doc", "Maintenance Cost", "Salary", "Insurance", "Depreciation",
        "Profit/(Loss)", "Departure DateTime", "Arrival DateTime", "Trip Duration (Days)", "Status"
    ])

    for s in shipments:
        vc = getattr(s, 'variable_cost', None)
        fare = Decimal(vc.fare) if vc else Decimal(0)
        recovery_fare = Decimal(vc.recovery_fare) if vc else Decimal(0)
        fuel_tk = Decimal(vc.fuel_tk) if vc else Decimal(0)
        toll = Decimal(vc.toll) if vc else Decimal(0)
        food = Decimal(vc.food) if vc else Decimal(0)
        repair = Decimal(vc.repair) if vc else Decimal(0)
        police = Decimal(vc.police) if vc else Decimal(0)
        without_doc = Decimal(vc.without_doc) if vc else Decimal(0)

        salary = Decimal(s.prorated_salary or 0)
        insurance = Decimal(s.prorated_insurance or 0)
        depriciation = Decimal(s.prorated_depriciation or 0)
        maintenance_cost = Decimal(s.maintenance_cost or 0)  # <-- use stored field


        # Use actual field values, not calculation
        up_fuel = round(s.fuel_ltr or 0, 2)
        remaining_fuel = round(s.remaining_fuel or 0, 2)
        fuel_consumption = round(s.fuel_consumption or 0, 2)  # <-- use actual property/field

        profit_loss = (fare + recovery_fare) - (
            fuel_tk + toll + food + repair + police + without_doc + maintenance_cost+ salary + insurance + depriciation
        )

        date_str = s.date.strftime("%b. %d, %Y").replace(" 0", " ")

        # Format date and datetime
        date_str = format_date(s.date)
        departure_str = format_date(s.departure_datetime)
        arrival_str = format_date(s.arrival_datetime)

        writer.writerow([
            s.trip_no,
            date_str,
            s.vehicle_no,
            s.vehicle_owner,
            s.origin,
            s.destination,
            s.item,
            up_fuel,
            remaining_fuel,
            fuel_consumption,
            round(fare, 2),
            round(recovery_fare, 2),
            round(fuel_tk, 2),
            round(toll, 2),
            round(food, 2),
            round(repair, 2),
            round(police, 2),
            round(without_doc, 2),
            round(maintenance_cost, 2),
            round(salary, 2),
            round(insurance, 2),
            round(depriciation, 2),
            round(profit_loss, 2),
            departure_str,
            arrival_str,
            s.trip_duration_days,  # already stored as integer days
            s.status
        ])
    return response

@user_passes_test(lambda u: u.is_superuser)
def shipment_undo(request, shipment_id):
    shipment = get_object_or_404(Shipment, id=shipment_id)

    if shipment.status == "Posted":
        shipment.status = "New"
        shipment.save()
        messages.success(request, f"Shipment {shipment.trip_no} is now editable again.")
    else:
        messages.warning(request, f"Shipment {shipment.trip_no} is not posted, cannot undo.")

    return redirect("shipment_list")

@login_required
def shipment_delete(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)

    if shipment.status != "New":
        messages.error(request, "Only shipments with status 'New' can be deleted.")
        return redirect("shipment_list")  # or your URL name

    shipment.delete()
    messages.success(request, f"Shipment {shipment.trip_no} deleted successfully.")
    return redirect("shipment_list")


@login_required
def create_shipment(request):
    if request.method == "POST":
        # Get global fixed cost fallback
        fixed_cost_config = FixedCostConfig.objects.first()
        salary_total = Decimal(fixed_cost_config.salary) if fixed_cost_config else Decimal(0)
        insurance_total = Decimal(fixed_cost_config.insurance) if fixed_cost_config else Decimal(0)

        shipment_date = request.POST.get("date")

        # Count all "New" trips on the same date (including this one)
        existing_trips_count = Shipment.objects.filter(date=shipment_date, status="New").count()
        total_trips = existing_trips_count + 1  # include the current shipment

        # Prorate fixed costs
        prorated_salary = salary_total / total_trips
        prorated_insurance = insurance_total / total_trips

        # Create the shipment with snapshot values
        shipment = Shipment.objects.create(
            trip_no=request.POST.get("trip_no"),
            date=shipment_date,
            vehicle_no=request.POST.get("vehicle_no"),
            vehicle_owner = request.POST.get("vehicle_owner"),
            origin=request.POST.get("origin"),
            destination=request.POST.get("destination"),
            item=request.POST.get("item"),
            qty=request.POST.get("qty") or 0,
            fuel_ltr=request.POST.get("fuel_ltr") or 0,
            salary_snapshot=prorated_salary,
            insurance_snapshot=prorated_insurance,
            status="New",
        )

        return redirect("shipment_list")

    return render(request, "shipments/shipment_form.html")


# @login_required
# @user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="FixedCostAdmins").exists())
# def fixed_cost_config_view(request):
#     config = FixedCostConfig.objects.first()
#     if not config:
#         config = FixedCostConfig.objects.create(salary=0, insurance=0, depriciation=0)

#     if request.method == "POST":
#         form = FixedCostConfigForm(request.POST, instance=config)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Fixed costs updated successfully!")
#             return redirect('fixed_cost_config')
#     else:
#         form = FixedCostConfigForm(instance=config)

#     return render(request, "shipments/fixed_cost_config.html", {"form": form})

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from .models import FixedCostConfig
from .forms import FixedCostConfigForm

@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="FixedCostAdmins").exists())
def fixed_cost_config_view(request):
    edit_config = None

    # Check if editing an existing config (by GET param)
    if request.method == "GET" and "edit_id" in request.GET:
        edit_config = FixedCostConfig.objects.filter(id=request.GET.get("edit_id")).first()
        form = FixedCostConfigForm(instance=edit_config)
    
    # POST requests
    elif request.method == "POST":
        # Delete record if 'delete_id' exists
        if "delete_id" in request.POST:
            config_to_delete = FixedCostConfig.objects.filter(id=request.POST.get("delete_id")).first()
            if config_to_delete:
                config_to_delete.delete()
                messages.success(request, "Fixed cost config deleted successfully.")
            return redirect("fixed_cost_config")

        # Update existing config if 'edit_id' exists, else create new
        edit_id = request.POST.get("edit_id")
        if edit_id:
            edit_config = FixedCostConfig.objects.filter(id=edit_id).first()
            form = FixedCostConfigForm(request.POST, instance=edit_config)
        else:
            form = FixedCostConfigForm(request.POST)

        if form.is_valid():
            config = form.save(commit=False)
            if not edit_id:  # only set created_by for new records
                config.created_by = request.user
            config.save()  # updated_at will update automatically if auto_now=True
            messages.success(request, "Fixed costs saved successfully.")

            # --- Recalculate prorated costs for shipments in this month/year ---
            shipments = Shipment.objects.filter(date__year=config.year, date__month=config.month)
            trip_count = shipments.count() or 1

            prorated_salary = (config.salary / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            prorated_insurance = (config.insurance / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            prorated_depriciation = (config.depriciation / trip_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            for shipment in shipments:
                shipment.prorated_salary = prorated_salary
                shipment.prorated_insurance = prorated_insurance
                shipment.prorated_depriciation = prorated_depriciation
                shipment.save(update_fields=['prorated_salary', 'prorated_insurance', 'prorated_depriciation'])

            return redirect("fixed_cost_config")
    else:
        # Default form for new entry
        config = FixedCostConfig.objects.first()
        form = FixedCostConfigForm(instance=config)

    # List all configs to display in the template
    fixed_cost_list = FixedCostConfig.objects.all().order_by('-year', '-month')
    
    return render(request, "shipments/fixed_cost_config.html", {
        "form": form,
        "fixed_cost_list": fixed_cost_list,
        "edit_config": edit_config,
        "user": request.user,  # optional, if you want to show in template
    })


@login_required

def dashboard(request):
    shipments = Shipment.objects.all().select_related("variable_cost")

    # Ensure variable_cost exists for all shipments
    for s in shipments:
        if not hasattr(s, 'variable_cost') or s.variable_cost is None:
            s.variable_cost = type('VC', (), {
                'fare': Decimal('0.00'), 'recovery_fare': Decimal('0.00'),
                'fuel_tk': Decimal('0.00'), 'toll': Decimal('0.00'), 'food': Decimal('0.00'),
                'repair': Decimal('0.00'), 'police': Decimal('0.00'), 'without_doc': Decimal('0.00')
            })()

    # --- Filter by date if provided ---
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date and to_date:
        shipments = shipments.filter(date__range=[from_date, to_date])

    # --- Ensure variable_cost exists for all shipments ---
    for s in shipments:
        if not hasattr(s, 'variable_cost') or s.variable_cost is None:
            s.variable_cost = type('VC', (), {
                'fare': Decimal('0.00'), 'recovery_fare': Decimal('0.00'),
                'fuel_tk': Decimal('0.00'), 'toll': Decimal('0.00'), 'food': Decimal('0.00'),
                'repair': Decimal('0.00'), 'police': Decimal('0.00'), 'without_doc': Decimal('0.00')
            })()



    # --- KPI Calculations ---
    total_revenue = sum(
        Decimal(s.variable_cost.fare) + Decimal(s.variable_cost.recovery_fare) for s in shipments
    )
    total_cost = sum(
        Decimal(s.variable_cost.fuel_tk) + Decimal(s.variable_cost.toll) + Decimal(s.variable_cost.food) +
        Decimal(s.variable_cost.repair) + Decimal(s.variable_cost.police) + Decimal(s.variable_cost.without_doc) +
        (s.prorated_salary or Decimal('0.00')) + (s.prorated_insurance or Decimal('0.00')) + (s.prorated_depriciation or Decimal('0.00'))
        for s in shipments
    )
    total_profit = total_revenue - total_cost
    avg_profit_margin = (total_profit / total_revenue * 100) if total_revenue else Decimal('0.00')
    total_shipments = shipments.count()

    # --- Average Revenue, Cost & Profit per Trip ---
    avg_revenue_per_trip = (total_revenue / total_shipments) if total_shipments else Decimal('0.00')
    avg_cost_per_trip = (total_cost / total_shipments) if total_shipments else Decimal('0.00')
    avg_profit_per_trip = (total_profit / total_shipments) if total_shipments else Decimal('0.00')

    # --- Shipment Status Counts ---
    status_counts = shipments.values('status').annotate(count=Count('id'))
    status_dict = {item['status']: item['count'] for item in status_counts}
    status_labels = list(status_dict.keys())
    status_values = list(status_dict.values())

    # --- Daily Revenue, Cost & Profit ---
    daily_data = defaultdict(lambda: {'revenue': Decimal('0.00'), 'cost': Decimal('0.00')})
    for s in shipments:
        day = s.date.strftime("%Y-%m-%d")
        rev = Decimal(s.variable_cost.fare) + Decimal(s.variable_cost.recovery_fare)
        cost = (Decimal(s.variable_cost.fuel_tk) + Decimal(s.variable_cost.toll) + Decimal(s.variable_cost.food) +
                Decimal(s.variable_cost.repair) + Decimal(s.variable_cost.police) + Decimal(s.variable_cost.without_doc) +
                (s.prorated_salary or Decimal('0.00')) + (s.prorated_insurance or Decimal('0.00')) + (s.prorated_depriciation or Decimal('0.00')))
        daily_data[day]['revenue'] += rev
        daily_data[day]['cost'] += cost

    chart_labels = sorted(daily_data.keys())
    chart_revenue = [float(daily_data[d]['revenue']) for d in chart_labels]
    chart_cost = [float(daily_data[d]['cost']) for d in chart_labels]
    chart_profit = [chart_revenue[i] - chart_cost[i] for i in range(len(chart_labels))]

    # --- Revenue & Profit per Vehicle ---
    vehicle_revenue = defaultdict(Decimal)
    vehicle_profit = defaultdict(Decimal)
    for s in shipments:
        rev = Decimal(s.variable_cost.fare) + Decimal(s.variable_cost.recovery_fare)
        cost = (Decimal(s.variable_cost.fuel_tk) + Decimal(s.variable_cost.toll) + Decimal(s.variable_cost.food) +
                Decimal(s.variable_cost.repair) + Decimal(s.variable_cost.police) + Decimal(s.variable_cost.without_doc) +
                (s.prorated_salary or Decimal('0.00')) + (s.prorated_insurance or Decimal('0.00')) + (s.prorated_depriciation or Decimal('0.00')))
        vehicle_revenue[s.vehicle_no] += rev
        vehicle_profit[s.vehicle_no] += rev - cost

    top_vehicle_revenue_list = sorted(vehicle_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    top_vehicle_labels = [v[0] for v in top_vehicle_revenue_list]
    top_vehicle_revenue = [float(v[1]) for v in top_vehicle_revenue_list]

    top_vehicle_profit_list = sorted(vehicle_profit.items(), key=lambda x: x[1], reverse=True)[:5]
    top_vehicle_profit_labels = [v[0] for v in top_vehicle_profit_list]
    top_vehicle_profit_values = [float(v[1]) for v in top_vehicle_profit_list]

    # --- Profit per Owner ---
    owner_profit = defaultdict(Decimal)
    for s in shipments:
        rev = Decimal(s.variable_cost.fare) + Decimal(s.variable_cost.recovery_fare)
        cost = (Decimal(s.variable_cost.fuel_tk) + Decimal(s.variable_cost.toll) + Decimal(s.variable_cost.food) +
                Decimal(s.variable_cost.repair) + Decimal(s.variable_cost.police) + Decimal(s.variable_cost.without_doc) +
                (s.prorated_salary or Decimal('0.00')) + (s.prorated_insurance or Decimal('0.00')) + (s.prorated_depriciation or Decimal('0.00')))
        owner_profit[s.vehicle_owner] += rev - cost

    top_owner_profit_list = sorted(owner_profit.items(), key=lambda x: x[1], reverse=True)[:5]
    top_owner_labels = [v[0] for v in top_owner_profit_list]
    top_owner_profit_values = [float(v[1]) for v in top_owner_profit_list]

    # --- Cost Breakdown ---
    total_fuel = sum(Decimal(s.variable_cost.fuel_tk) for s in shipments)
    total_toll = sum(Decimal(s.variable_cost.toll) for s in shipments)
    total_food = sum(Decimal(s.variable_cost.food) for s in shipments)
    total_repair = sum(Decimal(s.variable_cost.repair) for s in shipments)
    total_police = sum(Decimal(s.variable_cost.police) for s in shipments)
    total_without_doc = sum(Decimal(s.variable_cost.without_doc) for s in shipments)
    total_salary = sum(s.prorated_salary or Decimal('0.00') for s in shipments)
    total_insurance = sum(s.prorated_insurance or Decimal('0.00') for s in shipments)
    total_depr = sum(s.prorated_depriciation or Decimal('0.00') for s in shipments)

    cost_breakdown_labels = ['Fuel', 'Toll', 'Food', 'Repair', 'Police', 'Without Doc', 'Salary', 'Insurance', 'Depreciation']
    cost_breakdown_values = [float(total_fuel), float(total_toll), float(total_food), float(total_repair),
                             float(total_police), float(total_without_doc), float(total_salary),
                             float(total_insurance), float(total_depr)]

    # --- Trip Profits (Descending by Profit) ---
    trip_profit_map = defaultdict(Decimal)
    for s in shipments:
        profit = (Decimal(s.variable_cost.fare) + Decimal(s.variable_cost.recovery_fare) -
                  (Decimal(s.variable_cost.fuel_tk) + Decimal(s.variable_cost.toll) + Decimal(s.variable_cost.food) +
                   Decimal(s.variable_cost.repair) + Decimal(s.variable_cost.police) + Decimal(s.variable_cost.without_doc) +
                   (s.prorated_salary or Decimal('0.00')) + (s.prorated_insurance or Decimal('0.00')) + (s.prorated_depriciation or Decimal('0.00'))))
        trip_profit_map[s.trip_no] += profit

    top_10_trips_by_profit = sorted(trip_profit_map.items(), key=lambda x: x[1], reverse=True)[:9]

    # --- Thresholds ---
    high_cost_threshold = float(total_cost / total_shipments * Decimal('1.5')) if total_shipments else 0
    low_revenue_threshold = float(total_revenue / total_shipments * Decimal('0.5')) if total_shipments else 0
    is_fixed_cost_admin = request.user.groups.filter(name="FixedCostAdmins").exists() if request.user.is_authenticated else False


    context = {
        'total_revenue': float(total_revenue),
        'total_cost': float(total_cost),
        'total_profit': float(total_profit),
        'avg_profit_margin': Decimal(avg_profit_margin).quantize(Decimal('0.01')),
        'total_shipments': total_shipments,
        'avg_revenue_per_trip': float(avg_revenue_per_trip),
        'avg_cost_per_trip': float(avg_cost_per_trip),
        'avg_profit_per_trip': float(avg_profit_per_trip),

        'status_dict': status_dict,
        'status_labels': status_labels,
        'status_values': status_values,

        'chart_labels': chart_labels,
        'chart_revenue': chart_revenue,
        'chart_cost': chart_cost,
        'chart_profit': chart_profit,

        'top_vehicle_labels': top_vehicle_labels,
        'top_vehicle_revenue': top_vehicle_revenue,
        'top_vehicle_profit_labels': top_vehicle_profit_labels,
        'top_vehicle_profit_values': top_vehicle_profit_values,

        'top_owner_labels': top_owner_labels,
        'top_owner_profit': top_owner_profit_values,

        'cost_breakdown_labels': cost_breakdown_labels,
        'cost_breakdown_values': cost_breakdown_values,

        'top_10_trips_by_profit': [{"trip_no": t[0], "profit": float(t[1])} for t in top_10_trips_by_profit],

        'high_cost_threshold': high_cost_threshold,
        'low_revenue_threshold': low_revenue_threshold,

        # Pass the GET params to keep the form values
        'from_date': from_date,
        'to_date': to_date,
        'is_fixed_cost_admin': is_fixed_cost_admin,

    }

    return render(request, "dashboard.html", context)



from .forms import VehicleMaintenanceForm
from .models import VehicleMaintenance

# @login_required
# @user_passes_test(lambda u: u.is_superuser)
# def manage_vehicle_maintenance(request):
#     if request.method == "POST":
#         form = VehicleMaintenanceForm(request.POST)
#         if form.is_valid():
#             vm = form.save(commit=False)
#             vm.created_by = request.user
#             vm.save()
#             return redirect('manage_vehicle_maintenance')
#     else:
#         form = VehicleMaintenanceForm()

#     vehicle_maintenance_list = VehicleMaintenance.objects.all().order_by('-year', '-month')
#     return render(request, 'shipments/manage_vehicle_maintenance.html', {
#         'form': form,
#         'vehicle_maintenance_list': vehicle_maintenance_list
#     })


# views.py
from django.shortcuts import render, redirect
from .models import VehicleMaintenance, Shipment
from .forms import VehicleMaintenanceForm
from django.contrib import messages

from decimal import Decimal, ROUND_HALF_UP
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import VehicleMaintenance, Shipment
from .forms import VehicleMaintenanceForm

from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import VehicleMaintenance, Shipment
from .forms import VehicleMaintenanceForm

def manage_vehicle_maintenance(request):
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can access this page.")
        return redirect("dashboard")

    

    edit_vm = None
    if request.method == "GET" and "edit_id" in request.GET:
        edit_vm = VehicleMaintenance.objects.filter(id=request.GET.get("edit_id")).first()
        form = VehicleMaintenanceForm(instance=edit_vm)
    elif request.method == "POST":
        if "delete_id" in request.POST:
            vm_to_delete = VehicleMaintenance.objects.filter(id=request.POST.get("delete_id")).first()
            if vm_to_delete:
                vm_to_delete.delete()
                messages.success(request, "Vehicle maintenance record deleted successfully.")
            return redirect("manage_vehicle_maintenance")

        edit_id = request.POST.get("edit_id")
        if edit_id:
            edit_vm = VehicleMaintenance.objects.filter(id=edit_id).first()
            form = VehicleMaintenanceForm(request.POST, instance=edit_vm)
        else:
            form = VehicleMaintenanceForm(request.POST)

        if form.is_valid():
            vm = form.save(commit=False)
            vm.year = int(form.cleaned_data['year'])
            vm.created_by = request.user
            vm.save()

            # Pro-rate maintenance cost across shipments for this vehicle/month/year
            trips = Shipment.objects.filter(
                vehicle_no=vm.vehicle_no,
                date__year=vm.year,
                date__month=vm.month
            )
            if trips.exists():
                prorated_cost = (Decimal(vm.total_cost) / trips.count()).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                for t in trips:
                    t.maintenance_cost = prorated_cost
                    t.save(update_fields=['maintenance_cost'])

            messages.success(request, "Vehicle maintenance saved successfully.")
            return redirect("manage_vehicle_maintenance")
    else:
        form = VehicleMaintenanceForm()

    vehicle_maintenance_list = VehicleMaintenance.objects.all().order_by('-year', '-month')
    vehicles = list(global_vehicles)
    
    context = {
        'form': form,
        'vehicle_maintenance_list': vehicle_maintenance_list,
        'edit_vm': edit_vm,
        'vehicles': vehicles,  # important
    }
    return render(request, 'shipments/manage_vehicle_maintenance.html', context)



