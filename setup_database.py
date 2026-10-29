"""
setup_database.py  --  Run this ONCE before starting Asik.

    python setup_database.py            (create database + demo data)
    python setup_database.py --reset    (delete everything and start fresh)

What it does, step by step:
  1. Connects to MySQL using the values in config.py
  2. Runs schema.sql to create the database `asik_database` and all tables
  3. Loads the Philippine regions/provinces/municipalities (ph_locations.py)
     AND all barangays into the `barangays` table
  4. Adds DEMO data: demo accounts, mock farms/companies, job vacancies,
     and equipment for rent in every region.

Demo logins (username / password):
    admin       / admin123       -> Administrator
    seeker      / seeker123      -> Job seeker
    employer    / employer123    -> Employer
    lender      / lender123      -> Lender (rents out equipment)
    both        / both123        -> Employer AND Lender (can switch)

NOTE: Salaries are DEMO figures in Philippine pesos. The laborer rate is
anchored on the NCR agriculture minimum wage of PHP 718/day (effective
July 25, 2026, Wage Order NCR-27) and scaled down for other regions
(Bicol's agriculture minimum is PHP 455/day). Real wages differ by region and
wage order, so employers should always check their own regional rate.
"""

import os
import sys

import config
import database as db
from ph_locations import PH_LOCATIONS, PH_BARANGAYS

# ------------------------------------------------------------------
# Mock companies / farms:  name, street, municipality, province, region
# (the full address is built automatically below)
# ------------------------------------------------------------------
COMPANIES = [
    ("Golden Grain Farms Inc.", "Purok 3, Brgy. San Nicolas", "Magalang", "Pampanga", "Region III - Central Luzon"),
    ("Nueva Ecija Rice Cooperative", "Brgy. Sumacab Norte", "Cabanatuan City", "Nueva Ecija", "Region III - Central Luzon"),
    ("Benguet Highland Veggies Co.", "Km 5 Halsema Highway, Brgy. Pico", "La Trinidad", "Benguet", "CAR - Cordillera Administrative Region"),
    ("Ilocos Garlic & Tobacco Growers", "Brgy. Poblacion", "Laoag City", "Ilocos Norte", "Region I - Ilocos Region"),
    ("Isabela Corn Valley Agri-Corp", "Brgy. Garita", "Ilagan City", "Isabela", "Region II - Cagayan Valley"),
    ("Laguna Coco Estate", "Brgy. Bambang", "Los Banos", "Laguna", "Region IV-A - CALABARZON"),
    ("Batangas Cacao & Coffee Farm", "Brgy. Pinagtong-ulan", "Lipa City", "Batangas", "Region IV-A - CALABARZON"),
    ("Palawan Coconut Plantation", "Brgy. Irawan", "Puerto Princesa City", "Palawan", "Region IV-B - MIMAROPA"),
    ("Bicol Pili & Abaca Farms", "Brgy. Bagumbayan", "Legazpi City", "Albay", "Region V - Bicol Region"),
    ("Hacienda Dulce Negros", "Brgy. Mansilingan", "Bacolod City", "Negros Occidental", "Region VI - Western Visayas"),
    ("Cebu Highland Agri-Ventures", "Brgy. Valladolid", "Carcar City", "Cebu", "Region VII - Central Visayas"),
    ("Leyte Abaca & Rootcrops Corp.", "Brgy. Cogon", "Ormoc City", "Leyte", "Region VIII - Eastern Visayas"),
    ("Zamboanga Seaweed & Coconut Farm", "Brgy. Poblacion", "Dipolog City", "Zamboanga del Norte", "Region IX - Zamboanga Peninsula"),
    ("Bukidnon Pineapple Growers Inc.", "Brgy. Dicklum", "Manolo Fortich", "Bukidnon", "Region X - Northern Mindanao"),
    ("Davao Banana Export Farms", "Brgy. Gredu", "Panabo City", "Davao del Norte", "Region XI - Davao Region"),
    ("SOCCSKSARGEN Fruit Farms", "Brgy. Glamang", "Polomolok", "South Cotabato", "Region XII - SOCCSKSARGEN"),
    ("Caraga Palm & Rubber Estate", "Brgy. Ampayon", "Butuan City", "Agusan del Norte", "Region XIII - Caraga"),
    ("Bangsamoro Rice & Corn Growers", "Brgy. Poblacion", "Marawi City", "Lanao del Sur", "BARMM - Bangsamoro Region"),
    ("Metro Urban Farms Hub", "No. 12 Visayas Avenue", "Quezon City", "Metro Manila", "NCR - National Capital Region"),
]

# ------------------------------------------------------------------
# Job catalogue: title, level, description, base PHP/day (NCR basis),
#                days per week, hours per week
# ------------------------------------------------------------------
JOBS = [
    # ----- Laborers -----
    ("Farm Laborer", "Laborer", "General field work: land clearing, weeding, fertilizer application and hauling of farm materials.", 718, 6, 48),
    ("Harvester / Picker", "Laborer", "Hand-harvest rice, vegetables or fruit and sort the produce by grade during the harvest season.", 718, 6, 48),
    ("Planting Crew Member", "Laborer", "Transplant seedlings, sow seeds and maintain crop rows following the farm manager's plan.", 718, 6, 48),
    ("Packing House Worker", "Laborer", "Wash, weigh, pack and label produce for delivery to buyers and markets.", 718, 6, 48),
    # ----- Skilled -----
    ("Livestock Caretaker", "Skilled", "Feed, clean and monitor the health of poultry, hogs or cattle and keep daily health records.", 750, 6, 48),
    ("Tractor / Machine Operator", "Skilled", "Operate tractors, tillers, seeders and harvesters; perform daily machine checks and basic repairs.", 850, 6, 48),
    ("Irrigation Technician", "Skilled", "Install, maintain and repair irrigation pumps, canals, drip lines and smart irrigation controllers.", 900, 6, 48),
    ("Agricultural Drone Pilot", "Skilled", "Fly mapping and spraying drones, process aerial crop images and report field problems.", 1200, 5, 40),
    ("Farm Supervisor", "Skilled", "Lead the laborers, assign daily tasks, check attendance and report progress to the farm manager.", 1100, 6, 48),
    # ----- Experts -----
    ("Crop Protection Specialist", "Expert", "Identify pests and diseases, prepare integrated pest management plans and train workers.", 1400, 5, 40),
    ("Agricultural Engineer", "Expert", "Design farm structures, irrigation and mechanization systems and supervise their installation.", 1500, 5, 40),
    ("Agronomist", "Expert", "Plan crop programs, soil fertility and variety selection to raise yield and quality.", 1600, 5, 40),
    ("Soil Scientist", "Expert", "Run soil tests, interpret results and recommend lime, fertilizer and soil-health programs.", 1700, 5, 40),
    ("Farm Veterinarian", "Expert", "Provide animal health care, vaccination schedules and disease-prevention programs.", 1800, 5, 40),
    ("Farm Manager", "Expert", "Manage the whole farm operation: budget, staff, production targets and buyer relations.", 2000, 5, 40),
]

# Wage scale compared with NCR (demo estimate; Bicol 455/718 = 0.63 is from its wage order)
REGION_FACTOR = {
    "NCR - National Capital Region": 1.00,
    "Region V - Bicol Region": 0.63,
    "Region IV-A - CALABARZON": 0.88,
    "Region III - Central Luzon": 0.86,
    "Region VII - Central Visayas": 0.78,
}
DEFAULT_FACTOR = 0.72

# ------------------------------------------------------------------
# Equipment catalogue: name, icon, category, description, PHP/day
# ------------------------------------------------------------------
EQUIPMENT = [
    ("Agricultural Tractor", "🚜", "Heavy Equipment", "Field preparation and hauling", 2500),
    ("Heavy Duty Plow", "⚒", "Heavy Equipment", "Primary soil tillage", 1200),
    ("Combine Harvester", "🌾", "Heavy Equipment", "Harvesting and threshing", 6500),
    ("Disc Harrow", "⚙", "Heavy Equipment", "Soil breaking and cultivation", 1800),
    ("Mechanical Seeder", "🌱", "Heavy Equipment", "Mechanized seed placement", 2000),
    ("Rice Transplanter", "🌾", "Heavy Equipment", "Mechanized rice planting", 3500),
    ("Corn Harvester", "🌽", "Heavy Equipment", "Efficient corn harvesting", 5000),
    ("Land Leveler", "🚜", "Heavy Equipment", "Agricultural field leveling", 1500),
    ("Agricultural Drone", "🛸", "ICT Farming Tools", "Aerial mapping and crop monitoring", 2200),
    ("Spraying Drone", "🚁", "ICT Farming Tools", "Precision agricultural spraying", 3000),
    ("Smart Soil Sensor", "📡", "ICT Farming Tools", "Soil moisture monitoring", 350),
    ("Weather Station", "🌦", "ICT Farming Tools", "Temperature and rainfall monitoring", 800),
    ("Field Camera", "📷", "ICT Farming Tools", "Remote farm surveillance", 500),
    ("GPS Guidance System", "🛰", "ICT Farming Tools", "Precision machinery navigation", 1500),
    ("Smart Irrigation Controller", "💧", "ICT Farming Tools", "Automated irrigation control", 650),
    ("Crop Health Scanner", "🔬", "ICT Farming Tools", "Crop health assessment", 950),
]


def run_schema():
    """Execute schema.sql (comment lines are removed, then split on ';')."""
    path = os.path.join(config.BASE_DIR, "schema.sql")
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    conn = db.get_connection(with_database=False)
    cur = conn.cursor()
    for stmt in statements:
        cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()
    print("✔ Tables created")


def load_locations():
    """Copy PH_LOCATIONS and PH_BARANGAYS from ph_locations.py into the
    ph_locations and barangays MySQL tables.

    PH_BARANGAYS can have two shapes and both are handled:
        {region: {province: {municipality: [brgys...]}}}   <- normal
        {region: {province: [municipality, ...]}}          <- flat (city-only)
    """
    # ---- 1. create the barangays table if missing ----
    db.execute("""
        CREATE TABLE IF NOT EXISTS barangays (
            barangay_id  INT AUTO_INCREMENT PRIMARY KEY,
            region       VARCHAR(120) NOT NULL,
            province     VARCHAR(120) NOT NULL,
            municipality VARCHAR(120) NOT NULL,
            barangay     VARCHAR(150) NOT NULL,
            INDEX idx_muni (municipality),
            INDEX idx_muni_prov (municipality, province)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ---- 2. flatten PH_BARANGAYS, tolerating both shapes ----
    rows = []                 # (region, province, municipality, barangay)
    locations = set()         # (region, province, municipality)
    for region, provinces in PH_BARANGAYS.items():
        for province, munis in provinces.items():
            if isinstance(munis, dict):
                # normal shape: {municipality: [barangays]}
                for muni, brgys in munis.items():
                    locations.add((region, province, muni))
                    for brgy in brgys:
                        rows.append((region, province, muni, brgy))
            elif isinstance(munis, list):
                # flat shape: [municipality, municipality, ...]
                for muni in munis:
                    locations.add((region, province, muni))
            else:
                print(f"⚠ Skipping {region} / {province} (unexpected type {type(munis).__name__})")

    # ---- 3. reload ph_locations ----
    db.execute("DELETE FROM ph_locations")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO ph_locations (region, province, municipality) "
        "VALUES (%s,%s,%s)",
        sorted(locations))
    conn.commit()

    # ---- 4. reload barangays ----
    db.execute("TRUNCATE TABLE barangays")
    BATCH = 2000
    for i in range(0, len(rows), BATCH):
        cur.executemany(
            "INSERT INTO barangays (region, province, municipality, barangay) "
            "VALUES (%s,%s,%s,%s)",
            rows[i:i + BATCH])
        conn.commit()

    cur.close()
    conn.close()
    print(f"✔ {len(locations):,} locations and {len(rows):,} barangays loaded")


def first_place(region):
    """First province/municipality of a region (default equipment location)."""
    prov = list(PH_LOCATIONS[region].keys())[0]
    return prov, PH_LOCATIONS[region][prov][0]


def seed_demo_data():
    """Insert demo accounts, companies, vacancies, equipment, etc."""
    # ---------- demo accounts ----------
    admin = db.create_account("admin", "admin123", "Asik Administrator", ["admin"],
                              "admin@asik.ph", "0917-000-0001",
                              "NCR - National Capital Region", "Metro Manila", "Quezon City")
    seeker = db.create_account("seeker", "seeker123", "Juan Dela Cruz", ["job_seeker"],
                               "juan@example.com", "0917-111-2222",
                               "Region III - Central Luzon", "Pampanga", "Angeles City",
                               "Brgy. Balibago")
    employer = db.create_account("employer", "employer123", "Maria Santos", ["employer"],
                                 "maria@goldengrain.ph", "0917-333-4444",
                                 "Region III - Central Luzon", "Pampanga", "Magalang")
    lender = db.create_account("lender", "lender123", "Pedro Reyes", ["lender"],
                               "pedro@example.com", "0917-555-6666",
                               "Region III - Central Luzon", "Tarlac", "Tarlac City")
    both = db.create_account("both", "both123", "Ana Villanueva", ["employer", "lender"],
                             "ana@example.com", "0917-777-8888",
                             "Region VII - Central Visayas", "Cebu", "Carcar City")

    # ---------- companies ----------
    company_ids = []
    for name, street, muni, prov, region in COMPANIES:
        full = f"{street}, {muni}, {prov}, {region}, Philippines"
        cid = db.execute(
            "INSERT INTO companies (company_name, street, municipality, province, "
            "region, full_address) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, street, muni, prov, region, full))
        company_ids.append(cid)

    # the demo employer manages the first company, 'both' manages the Cebu one
    db.execute("UPDATE companies SET owner_user_id=%s WHERE company_id=%s",
               (employer, company_ids[0]))
    db.execute("UPDATE companies SET owner_user_id=%s WHERE company_id=%s",
               (both, company_ids[10]))
    db.execute("INSERT INTO employer_details (user_id, company_id, position_title, "
               "business_permit, contact_number) VALUES (%s,%s,'Owner','DTI-2026-0001','0917-333-4444')",
               (employer, company_ids[0]))
    db.execute("INSERT INTO employer_details (user_id, company_id, position_title, "
               "business_permit, contact_number) VALUES (%s,%s,'HR Manager','DTI-2026-0002','0917-777-8888')",
               (both, company_ids[10]))

    # ---------- vacancies: 2 laborer + 1 skilled + 1 expert for each company ----------
    laborers = [j for j in JOBS if j[1] == "Laborer"]
    skilled = [j for j in JOBS if j[1] == "Skilled"]
    experts = [j for j in JOBS if j[1] == "Expert"]
    owner_of = {company_ids[0]: employer, company_ids[10]: both}
    first_vacancy = None
    for i, (cid, comp) in enumerate(zip(company_ids, COMPANIES)):
        factor = REGION_FACTOR.get(comp[4], DEFAULT_FACTOR)
        picks = [laborers[i % len(laborers)], laborers[(i + 1) % len(laborers)],
                 skilled[i % len(skilled)], experts[i % len(experts)]]
        for title, level, desc, base, days, hours in picks:
            salary = round(base * factor / 5) * 5          # round to nearest PHP 5
            vid = db.execute(
                "INSERT INTO job_vacancies (company_id, posted_by, job_title, job_level, "
                "description, salary_per_day, days_per_week, hours_per_week, slots) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, owner_of.get(cid), title, level, desc, salary, days, hours,
                 3 if level == "Laborer" else 1))
            if first_vacancy is None:
                first_vacancy = (vid, cid)

    # ---------- one demo application so the employer portal is not empty ----------
    vid, cid = first_vacancy
    db.execute(
        "INSERT INTO job_applications (applicant_id, vacancy_id, company_id, full_name, age, "
        "contact_number, email, region, province, municipality, address, skills, experience) "
        "VALUES (%s,%s,%s,'Juan Dela Cruz',27,'0917-111-2222','juan@example.com',"
        "'Region III - Central Luzon','Pampanga','Angeles City','Brgy. Balibago',"
        "'Planting, weeding, basic machinery','3 years working in a rice farm')",
        (seeker, vid, cid))

    # ---------- equipment in every region (4 items each) ----------
    owners = [None, lender, both, lender]
    n = 0
    for r_index, region in enumerate(PH_LOCATIONS):
        provs = list(PH_LOCATIONS[region].keys())
        for k in range(4):
            name, icon, cat, desc, price = EQUIPMENT[(r_index * 4 + k) % len(EQUIPMENT)]
            prov = provs[k % len(provs)]
            muni = PH_LOCATIONS[region][prov][0]
            # small price difference per region so the list looks realistic
            price = round(price * (0.9 + 0.05 * ((r_index + k) % 5)) / 50) * 50 or price
            owner = owners[k]
            if region.startswith("Region III") and k == 0:
                owner = lender                     # keep the demo lender in Central Luzon
            db.execute(
                "INSERT INTO equipment (owner_user_id, name, icon, category, description, "
                "price_per_day, region, province, municipality) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (owner, name, icon, cat, desc, price, region, prov, muni))
            n += 1

    # ---------- a welcome message ----------
    db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (%s,%s,%s)",
               (employer, seeker, "Hello Juan! Thanks for applying at Golden Grain Farms. "
                                  "Are you available for an interview this week?"))
    print(f"✔ Demo data added ({len(COMPANIES)} companies, {len(company_ids) * 4} vacancies, {n} equipment)")


def main():
    reset = "--reset" in sys.argv
    if reset:
        conn = db.get_connection(with_database=False)
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {config.DB_NAME}")
        conn.commit()
        conn.close()
        print("✔ Old database deleted")
    run_schema()
    load_locations()
    already = db.fetch_one("SELECT COUNT(*) AS n FROM account_credentials")["n"]
    if already:
        print("Demo data skipped (accounts already exist). Use --reset to rebuild.")
    else:
        seed_demo_data()
    print("\nDone! Start the app with:  python main.py")


if __name__ == "__main__":
    main()