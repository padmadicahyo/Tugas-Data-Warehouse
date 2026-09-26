import random, csv, os, zipfile, math, json, sys, subprocess
from datetime import date, datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

SEED = 20260923
random.seed(SEED)

# ------------------------------------------------------------
# COLAB / LOCAL PATH CONFIGURATION
# ------------------------------------------------------------
# Google Colab uses /content. For local execution, the current working
# directory is used. Override with environment variable DWBI_BASE_DIR.
IN_COLAB = "google.colab" in sys.modules or Path("/content").exists()
DEFAULT_BASE_DIR = Path("/content") if IN_COLAB else Path.cwd()
BASE_DIR = Path(os.environ.get("DWBI_BASE_DIR", str(DEFAULT_BASE_DIR))).resolve()

ROOT = BASE_DIR / "ecommerce_dwbi_scenario"
RAW = ROOT / "raw_sources"
MART = ROOT / "datamart"
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"
QUERY_RESULTS = ROOT / "query_results"
DUCKDB_PATH = ROOT / "ecommerce_dwbi.duckdb"
ZIP_PATH = BASE_DIR / "ecommerce_dwbi_scenario_20000_orders_colab_duckdb.zip"

for p in [RAW, MART, DOCS, SCRIPTS, QUERY_RESULTS]:
    p.mkdir(parents=True, exist_ok=True)

print(f"Environment : {'Google Colab' if IN_COLAB else 'Local Python'}")
print(f"Project root: {ROOT}")

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
N_ORDERS = 20_000
N_CUSTOMERS = 4_000
N_SELLERS = 300
N_PRODUCTS = 800
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 23)
HISTORY_START = date(2024, 1, 1)

cities = [
    ("Jakarta", "DKI Jakarta"), ("Bandung", "Jawa Barat"), ("Semarang", "Jawa Tengah"),
    ("Surakarta", "Jawa Tengah"), ("Yogyakarta", "DI Yogyakarta"), ("Surabaya", "Jawa Timur"),
    ("Malang", "Jawa Timur"), ("Sleman", "DI Yogyakarta"), ("Bantul", "DI Yogyakarta"),
    ("Bogor", "Jawa Barat"), ("Depok", "Jawa Barat"), ("Tangerang", "Banten"),
    ("Bekasi", "Jawa Barat"), ("Denpasar", "Bali"), ("Medan", "Sumatera Utara"),
    ("Palembang", "Sumatera Selatan"), ("Makassar", "Sulawesi Selatan"),
    ("Balikpapan", "Kalimantan Timur"), ("Samarinda", "Kalimantan Timur"),
    ("Pontianak", "Kalimantan Barat")
]

first_names = [
    "Ahmad","Rizky","Dimas","Fajar","Bagas","Arif","Raka","Andi","Bima","Rafi",
    "Siti","Aulia","Nabila","Putri","Aisyah","Dewi","Nadia","Intan","Farah","Tiara",
    "Yoga","Bayu","Naufal","Hendra","Ilham","Galih","Reza","Adit","Rina","Maya"
]
last_names = [
    "Pratama","Saputra","Hidayat","Wijaya","Nugroho","Setiawan","Ramadhan","Kurniawan",
    "Permana","Santoso","Lestari","Utami","Wulandari","Anggraini","Puspitasari",
    "Rahmawati","Firmansyah","Maulana","Hakim","Syahputra"
]

def random_address():
    city, province = random.choice(cities)
    return f"Jl. {random.choice(['Merdeka','Melati','Kenanga','Diponegoro','Sudirman','Gajah Mada','Pemuda','Veteran'])} No. {random.randint(1,250)}", city, province

def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

# ------------------------------------------------------------
# RAW MASTER: CUSTOMERS + ADDRESS HISTORY (SCD SOURCE)
# ------------------------------------------------------------
customer_base = []
customer_address_events = []
customer_versions = defaultdict(list)

for i in range(1, N_CUSTOMERS + 1):
    customer_id = f"CUST{i:05d}"
    fn, ln = random.choice(first_names), random.choice(last_names)
    name = f"{fn} {ln}"
    email = f"{fn}.{ln}.{i}@example.com".lower()
    gender = random.choice(["M", "F"])
    join_dt = HISTORY_START + timedelta(days=random.randint(0, (START_DATE - HISTORY_START).days))

    # Initial address
    street, city, province = random_address()
    events = [(HISTORY_START, street, city, province, "INITIAL")]

    # SCD scenario: ~18% move once, ~3% move twice
    r = random.random()
    n_moves = 2 if r < 0.03 else (1 if r < 0.18 else 0)
    move_dates = sorted(random.sample(
        [START_DATE + timedelta(days=x) for x in range((END_DATE - START_DATE).days + 1)],
        n_moves
    )) if n_moves else []

    for md in move_dates:
        nstreet, ncity, nprovince = random_address()
        while ncity == events[-1][2]:
            nstreet, ncity, nprovince = random_address()
        events.append((md, nstreet, ncity, nprovince, "MOVE"))

    for ev_date, st, ct, pr, ev_type in events:
        customer_address_events.append([
            f"CAE{len(customer_address_events)+1:07d}", customer_id, ev_date.isoformat(),
            st, ct, pr, ev_type
        ])
        customer_versions[customer_id].append((ev_date, st, ct, pr))

    latest = events[-1]
    customer_base.append([
        customer_id, name, email, gender, join_dt.isoformat(),
        latest[1], latest[2], latest[3]
    ])

# ------------------------------------------------------------
# RAW MASTER: SELLERS
# ------------------------------------------------------------
seller_prefix = ["Toko","Mart","Shop","Store","Grosir","Pusat","Outlet"]
seller_words = ["Nusantara","Sejahtera","Makmur","Jaya","Berkah","Prima","Sentosa","Mandiri","Cemerlang","Sukses",
                "Digital","Karya","Abadi","Gemilang","Mitra","Amanah","Maju","Lestari","Pangan","Tekno"]

seller_base = []
for i in range(1, N_SELLERS + 1):
    seller_id = f"SELL{i:04d}"
    st, ct, pr = random_address()
    seller_base.append([
        seller_id,
        f"{random.choice(seller_prefix)} {random.choice(seller_words)} {i:03d}",
        random.choice(["Micro", "Small", "Medium", "Enterprise"]),
        st, ct, pr,
        (HISTORY_START + timedelta(days=random.randint(0, 365))).isoformat(),
        "ACTIVE"
    ])

# ------------------------------------------------------------
# RAW MASTER: PRODUCTS + PRICE/HPP HISTORY
# ------------------------------------------------------------
categories = {
    "Elektronik": ["Earphone","Mouse","Keyboard","Power Bank","Charger","Lampu LED","Kabel Data","Speaker Mini"],
    "Fashion": ["Kaos","Kemeja","Jaket","Celana","Tas","Sepatu","Sandal","Topi"],
    "Rumah Tangga": ["Botol Minum","Rak Serbaguna","Wadah Makan","Handuk","Sprei","Bantal","Keset","Kotak Penyimpanan"],
    "Kecantikan": ["Facial Wash","Sunscreen","Moisturizer","Serum","Lip Tint","Body Lotion","Shampoo","Conditioner"],
    "Olahraga": ["Matras Yoga","Resistance Band","Skipping Rope","Botol Sport","Sarung Tangan Gym","Kaos Olahraga","Hand Grip","Tas Gym"],
    "Makanan": ["Kopi Bubuk","Teh Celup","Keripik","Granola","Biskuit","Madu","Sambal","Cokelat"],
    "Buku & ATK": ["Buku Tulis","Notebook","Pulpen","Pensil","Marker","Sticky Notes","Binder","Map Dokumen"],
    "Otomotif": ["Holder HP","Lap Microfiber","Pengharum Mobil","Kabel Jumper","Cover Motor","Sikat Detailing","Charger Mobil","Sarung Jok"]
}
brand_words = ["Arunika","Nusa","Velora","Kirana","Soluna","Pradana","Avero","Mavera","Elvano","Ravena"]

price_ranges = {
    "Elektronik": (35000, 900000), "Fashion": (30000, 500000),
    "Rumah Tangga": (15000, 350000), "Kecantikan": (18000, 300000),
    "Olahraga": (25000, 550000), "Makanan": (10000, 200000),
    "Buku & ATK": (5000, 150000), "Otomotif": (20000, 450000)
}

product_base = []
price_history = []
product_price_versions = defaultdict(list)

pid = 1
for category, item_names in categories.items():
    lo, hi = price_ranges[category]
    for j in range(100):
        product_id = f"PROD{pid:05d}"
        brand = random.choice(brand_words)
        product_name = f"{brand} {random.choice(item_names)} Series {j+1:03d}"
        product_base.append([product_id, product_name, brand, category, "ACTIVE"])

        # 2-5 price periods across history
        n_changes = random.choices([1,2,3,4], [0.15,0.40,0.30,0.15])[0]
        change_dates = sorted(random.sample(
            [START_DATE + timedelta(days=x) for x in range((END_DATE - START_DATE).days + 1)],
            n_changes
        ))
        periods = [HISTORY_START] + change_dates

        base_price = random.randrange(max(5000, lo), hi+1, 1000)
        current_price = base_price
        current_hpp = int(round(current_price * random.uniform(0.58, 0.82) / 1000) * 1000)

        for idx, eff in enumerate(periods):
            if idx > 0:
                current_price = max(5000, int(round(current_price * random.uniform(0.92,1.12) / 1000) * 1000))
                current_hpp = max(1000, int(round(current_price * random.uniform(0.58,0.82) / 1000) * 1000))
            price_history.append([
                f"PPH{len(price_history)+1:07d}", product_id, eff.isoformat(),
                current_price, current_hpp
            ])
            product_price_versions[product_id].append((eff, current_price, current_hpp))
        pid += 1

def price_as_of(product_id, order_date):
    versions = product_price_versions[product_id]
    valid = versions[0]
    for v in versions:
        if v[0] <= order_date:
            valid = v
        else:
            break
    return valid[1], valid[2]

# ------------------------------------------------------------
# REFERENCE MASTERS
# ------------------------------------------------------------
expeditions = [
    ["EXP01","Nusantara Express",11000,3],
    ["EXP02","Garuda Parcel",13000,3],
    ["EXP03","Lintas Kirim",10000,4],
    ["EXP04","Cepat Antar",15000,2],
    ["EXP05","Mitra Logistik",9000,5],
    ["EXP06","Urban Delivery",12000,3],
]
exp_lookup = {r[0]: r for r in expeditions}

payment_methods = [
    ["PAY01","Transfer Bank"],["PAY02","Virtual Account"],["PAY03","E-Wallet"],
    ["PAY04","QRIS"],["PAY05","Kartu Kredit/Debit"],["PAY06","COD"]
]
payment_lookup = {r[0]: r for r in payment_methods}

# ------------------------------------------------------------
# DATE SAMPLING WITH SEASONALITY
# ------------------------------------------------------------
all_dates = []
date_weights = []
d = START_DATE
while d <= END_DATE:
    w = 1.0
    if d.day >= 25 or d.day <= 3:
        w *= 1.35  # payday effect
    if d.month in [11,12]:
        w *= 1.35  # year-end campaigns
    if d.weekday() >= 5:
        w *= 1.10
    if d.year == 2026:
        w *= 1.12  # business growth
    all_dates.append(d)
    date_weights.append(w)
    d += timedelta(days=1)

customer_ids = [r[0] for r in customer_base]
seller_ids = [r[0] for r in seller_base]
product_ids = [r[0] for r in product_base]
exp_ids = [r[0] for r in expeditions]
pay_ids = [r[0] for r in payment_methods]

# Zipf-like customer/product popularity
customer_weights = [1 / ((i+1) ** 0.55) for i in range(N_CUSTOMERS)]
product_weights = [1 / ((i+1) ** 0.70) for i in range(N_PRODUCTS)]
seller_weights = [1 / ((i+1) ** 0.45) for i in range(N_SELLERS)]

# ------------------------------------------------------------
# RAW TRANSACTIONS
# ------------------------------------------------------------
orders = []
order_items = []
payments = []
shipments = []

for n in range(1, N_ORDERS + 1):
    order_id = f"ORD{n:08d}"
    order_date = random.choices(all_dates, weights=date_weights, k=1)[0]
    order_time = datetime.combine(order_date, datetime.min.time()) + timedelta(
        hours=random.randint(7,22), minutes=random.randint(0,59), seconds=random.randint(0,59)
    )
    customer_id = random.choices(customer_ids, weights=customer_weights, k=1)[0]
    seller_id = random.choices(seller_ids, weights=seller_weights, k=1)[0]
    payment_code = random.choices(pay_ids, [0.16,0.20,0.25,0.17,0.10,0.12], k=1)[0]
    expedition_code = random.choices(exp_ids, [0.18,0.17,0.20,0.15,0.17,0.13], k=1)[0]

    # Status distribution
    order_status = random.choices(
        ["COMPLETED","PROCESSING","CANCELLED","RETURNED"],
        [0.90,0.04,0.04,0.02], k=1
    )[0]

    # Outlier/bulk scenario ~0.7%
    is_bulk = random.random() < 0.007

    if is_bulk:
        item_count = random.randint(3, 7)
    else:
        item_count = random.choices([1,2,3,4,5], [0.31,0.34,0.20,0.10,0.05], k=1)[0]

    chosen_products = random.choices(product_ids, weights=product_weights, k=item_count)
    # Ensure distinct lines
    chosen_products = list(dict.fromkeys(chosen_products))
    while len(chosen_products) < item_count:
        p = random.choices(product_ids, weights=product_weights, k=1)[0]
        if p not in chosen_products:
            chosen_products.append(p)

    gross_subtotal = 0
    total_hpp = 0
    total_qty = 0
    temp_lines = []

    for line_no, product_id in enumerate(chosen_products, start=1):
        unit_price, unit_hpp = price_as_of(product_id, order_date)
        qty = random.randint(10,30) if is_bulk else random.choices([1,2,3,4,5], [0.64,0.22,0.08,0.04,0.02], k=1)[0]
        subtotal = unit_price * qty
        hpp_total = unit_hpp * qty
        gross_subtotal += subtotal
        total_hpp += hpp_total
        total_qty += qty
        temp_lines.append([
            f"OI{len(order_items)+len(temp_lines)+1:09d}", order_id, line_no, product_id,
            qty, unit_price, unit_hpp, subtotal, hpp_total
        ])

    # Promotions / order discount
    promo_code = ""
    discount_rate = 0.0
    if gross_subtotal >= 250_000 and random.random() < 0.45:
        promo_code, discount_rate = random.choice([
            ("HEMAT2",0.02),("HEMAT5",0.05),("SALE10",0.10),("MEGA15",0.15)
        ])
    total_discount = int(round(gross_subtotal * discount_rate / 1000) * 1000)
    total_discount = min(total_discount, gross_subtotal)

    # Shipping fee at order level
    base_shipping = exp_lookup[expedition_code][2]
    shipping_fee = base_shipping + max(0,total_qty-1)*1500 + random.choice([0,0,0,2000,3000,5000])
    checkout_total = gross_subtotal - total_discount + shipping_fee

    # Payment
    if order_status == "CANCELLED":
        payment_status = random.choices(["FAILED","EXPIRED","REFUNDED"], [0.55,0.30,0.15], k=1)[0]
    elif order_status == "RETURNED":
        payment_status = "REFUNDED"
    elif order_status == "PROCESSING":
        payment_status = random.choices(["PAID","PENDING"], [0.75,0.25], k=1)[0]
    else:
        payment_status = "PAID"

    payment_ts = None if payment_status in ["FAILED","EXPIRED","PENDING"] else order_time + timedelta(minutes=random.randint(1,180))
    amount_paid = 0 if payment_status in ["FAILED","EXPIRED"] else checkout_total

    # Shipment
    shipped_at = delivered_at = None
    shipping_status = "NOT_SHIPPED"
    late_delivery = False
    expected_days = exp_lookup[expedition_code][3]

    if order_status in ["COMPLETED","RETURNED"] or (order_status=="PROCESSING" and random.random() < 0.35):
        shipped_at = order_time + timedelta(hours=random.randint(8,72))
        if order_status == "PROCESSING":
            shipping_status = "IN_TRANSIT"
        else:
            late_delivery = random.random() < 0.09
            actual_days = expected_days + (random.randint(2,12) if late_delivery else random.randint(-1,1))
            actual_days = max(1, actual_days)
            delivered_at = shipped_at + timedelta(days=actual_days, hours=random.randint(1,10))
            shipping_status = "DELIVERED" if order_status == "COMPLETED" else "RETURNED"

    outlier_type = "BULK_ORDER" if is_bulk else ("HIGH_VALUE" if checkout_total >= 5_000_000 else "")

    orders.append([
        order_id, customer_id, seller_id, order_time.isoformat(sep=" "),
        order_status, payment_code, expedition_code, promo_code, total_discount,
        shipping_fee, gross_subtotal, checkout_total, is_bulk, outlier_type
    ])
    order_items.extend(temp_lines)
    payments.append([
        f"PMT{n:08d}", order_id, payment_code,
        payment_ts.isoformat(sep=" ") if payment_ts else "",
        amount_paid, payment_status
    ])
    shipments.append([
        f"SHP{n:08d}", order_id, expedition_code,
        shipped_at.isoformat(sep=" ") if shipped_at else "",
        delivered_at.isoformat(sep=" ") if delivered_at else "",
        shipping_status, shipping_fee, expected_days, "Y" if late_delivery else "N"
    ])

# ------------------------------------------------------------
# RAW FILES
# ------------------------------------------------------------
write_csv(RAW/"customers.csv",
          ["customer_id","customer_name","email","gender","join_date","current_street","current_city","current_province"],
          customer_base)
write_csv(RAW/"customer_address_history.csv",
          ["address_event_id","customer_id","effective_date","street","city","province","event_type"],
          customer_address_events)
write_csv(RAW/"sellers.csv",
          ["seller_id","seller_name","seller_segment","street","city","province","join_date","seller_status"],
          seller_base)
write_csv(RAW/"products.csv",
          ["product_id","product_name","brand","category","product_status"],
          product_base)
write_csv(RAW/"product_price_history.csv",
          ["price_event_id","product_id","effective_date","unit_price","unit_hpp"],
          price_history)
write_csv(RAW/"orders.csv",
          ["order_id","customer_id","seller_id","order_timestamp","order_status","payment_method_code",
           "expedition_code","promo_code","discount_amount","shipping_fee","gross_subtotal","checkout_total",
           "is_bulk_order","outlier_type"],
          orders)
write_csv(RAW/"order_items.csv",
          ["order_item_id","order_id","line_number","product_id","quantity","unit_price","unit_hpp",
           "gross_subtotal","total_hpp"],
          order_items)
write_csv(RAW/"payments.csv",
          ["payment_id","order_id","payment_method_code","payment_timestamp","amount_paid","payment_status"],
          payments)
write_csv(RAW/"shipments.csv",
          ["shipment_id","order_id","expedition_code","shipped_at","delivered_at","shipping_status",
           "shipping_fee","expected_delivery_days","late_delivery_flag"],
          shipments)
write_csv(RAW/"expeditions.csv",
          ["expedition_code","expedition_name","base_shipping_fee","sla_days"],
          expeditions)
write_csv(RAW/"payment_methods.csv",
          ["payment_method_code","payment_method_name"],
          payment_methods)

# ------------------------------------------------------------
# BUILD DIMENSIONS
# ------------------------------------------------------------

# Dim Date
dim_date = []
d = START_DATE
date_key_map = {}
dk = 1
while d <= END_DATE:
    row = [
        dk, d.isoformat(), d.day, d.month,
        d.strftime("%B"), ((d.month-1)//3)+1, d.year,
        d.isocalendar().week, d.strftime("%A"),
        "Y" if d.weekday() >= 5 else "N"
    ]
    dim_date.append(row)
    date_key_map[d] = dk
    dk += 1
    d += timedelta(days=1)

# Customer SCD2
dim_customer = []
customer_scd_map = defaultdict(list)
customer_base_lookup = {r[0]: r for r in customer_base}
customer_key = 1
for customer_id in customer_ids:
    base = customer_base_lookup[customer_id]
    versions = sorted(customer_versions[customer_id], key=lambda x: x[0])
    for idx, (eff, st, ct, pr) in enumerate(versions):
        end_eff = versions[idx+1][0] - timedelta(days=1) if idx+1 < len(versions) else date(9999,12,31)
        is_current = "Y" if idx == len(versions)-1 else "N"
        dim_customer.append([
            customer_key, customer_id, base[1], base[2], base[3], base[4],
            st, ct, pr, eff.isoformat(), end_eff.isoformat(), is_current
        ])
        customer_scd_map[customer_id].append((eff, end_eff, customer_key))
        customer_key += 1

def customer_key_as_of(customer_id, dt):
    for eff, end_eff, key in customer_scd_map[customer_id]:
        if eff <= dt <= end_eff:
            return key
    raise KeyError((customer_id, dt))

# Seller dimension
dim_seller = []
seller_key_map = {}
for idx, r in enumerate(seller_base, start=1):
    seller_key_map[r[0]] = idx
    dim_seller.append([idx] + r)

# Product dimension
dim_product = []
product_key_map = {}
for idx, r in enumerate(product_base, start=1):
    product_key_map[r[0]] = idx
    dim_product.append([idx] + r)

# Expedition and payment dimensions
dim_expedition = []
exp_key_map = {}
for idx, r in enumerate(expeditions, start=1):
    exp_key_map[r[0]] = idx
    dim_expedition.append([idx] + r)

dim_payment = []
payment_key_map = {}
for idx, r in enumerate(payment_methods, start=1):
    payment_key_map[r[0]] = idx
    dim_payment.append([idx] + r)

# Junk dimension: order/payment/shipment states + flags
payment_by_order = {r[1]: r for r in payments}
shipment_by_order = {r[1]: r for r in shipments}
status_combo_to_key = {}
dim_order_status = []

def get_status_key(order_status, payment_status, shipment_status, promo_flag, bulk_flag, late_flag):
    combo = (order_status, payment_status, shipment_status, promo_flag, bulk_flag, late_flag)
    if combo not in status_combo_to_key:
        key = len(status_combo_to_key) + 1
        status_combo_to_key[combo] = key
        dim_order_status.append([key] + list(combo))
    return status_combo_to_key[combo]

# ------------------------------------------------------------
# BUILD FACTS
# ------------------------------------------------------------
items_by_order = defaultdict(list)
for r in order_items:
    items_by_order[r[1]].append(r)

fact_sales = []
fact_sales_item = []
item_key = 1

for o in orders:
    order_id, customer_id, seller_id = o[0], o[1], o[2]
    order_dt = datetime.fromisoformat(o[3])
    order_date = order_dt.date()
    order_status = o[4]
    payment_code = o[5]
    expedition_code = o[6]
    promo_code = o[7]
    discount_amount = int(o[8])
    shipping_fee = int(o[9])
    gross_subtotal = int(o[10])
    checkout_total = int(o[11])
    bulk_flag = "Y" if o[12] else "N"

    p = payment_by_order[order_id]
    s = shipment_by_order[order_id]
    payment_status = p[5]
    shipment_status = s[5]
    late_flag = s[8]
    promo_flag = "Y" if promo_code else "N"

    status_key = get_status_key(order_status, payment_status, shipment_status, promo_flag, bulk_flag, late_flag)
    ckey = customer_key_as_of(customer_id, order_date)
    skey = seller_key_map[seller_id]
    ekey = exp_key_map[expedition_code]
    pkey = payment_key_map[payment_code]
    order_date_key = date_key_map[order_date]

    shipped_date_key = None
    delivered_date_key = None
    delivery_days = None
    if s[3]:
        shipped_date = datetime.fromisoformat(s[3]).date()
        if START_DATE <= shipped_date <= END_DATE:
            shipped_date_key = date_key_map[shipped_date]
    if s[4]:
        delivered_date = datetime.fromisoformat(s[4]).date()
        if START_DATE <= delivered_date <= END_DATE:
            delivered_date_key = date_key_map[delivered_date]
        if s[3]:
            delivery_days = (datetime.fromisoformat(s[4]) - datetime.fromisoformat(s[3])).days

    order_lines = items_by_order[order_id]
    jumlah_item = len(order_lines)
    total_quantity = sum(int(x[4]) for x in order_lines)
    total_hpp = sum(int(x[8]) for x in order_lines)
    net_product_sales = gross_subtotal - discount_amount
    profit = net_product_sales - total_hpp

    fact_sales.append([
        order_id, ckey, skey, ekey, pkey, order_date_key,
        shipped_date_key, delivered_date_key, status_key,
        jumlah_item, total_quantity, gross_subtotal, discount_amount,
        net_product_sales, shipping_fee, checkout_total, total_hpp, profit,
        delivery_days
    ])

    # Allocate order discount proportionally to items; force exact reconciliation.
    gross_values = [int(x[7]) for x in order_lines]
    allocs = []
    allocated_so_far = 0
    for i, gross in enumerate(gross_values):
        if i == len(gross_values)-1:
            alloc = discount_amount - allocated_so_far
        else:
            alloc = int(round(discount_amount * gross / gross_subtotal)) if gross_subtotal else 0
            allocated_so_far += alloc
        allocs.append(alloc)

    for raw_line, alloc_discount in zip(order_lines, allocs):
        _, _, line_no, product_id, qty, unit_price, unit_hpp, gross_line, total_hpp_line = raw_line
        net_sales = int(gross_line) - alloc_discount
        profit_item = net_sales - int(total_hpp_line)
        fact_sales_item.append([
            item_key, raw_line[0], order_id,
            ckey, skey, product_key_map[product_id], order_date_key,
            int(line_no), int(qty), int(unit_price), int(unit_hpp),
            int(gross_line), int(alloc_discount), int(net_sales),
            int(total_hpp_line), int(profit_item)
        ])
        item_key += 1

# ------------------------------------------------------------
# MART VALIDATION
# ------------------------------------------------------------
assert len(fact_sales) == N_ORDERS
assert len({r[0] for r in fact_sales}) == N_ORDERS

header_by_order = {r[0]: r for r in fact_sales}
recon = defaultdict(lambda: {"gross":0,"discount":0,"net":0,"hpp":0,"profit":0,"qty":0,"lines":0})
for r in fact_sales_item:
    oid = r[2]
    recon[oid]["lines"] += 1
    recon[oid]["qty"] += r[8]
    recon[oid]["gross"] += r[11]
    recon[oid]["discount"] += r[12]
    recon[oid]["net"] += r[13]
    recon[oid]["hpp"] += r[14]
    recon[oid]["profit"] += r[15]

for oid, h in header_by_order.items():
    rr = recon[oid]
    assert h[9] == rr["lines"]
    assert h[10] == rr["qty"]
    assert h[11] == rr["gross"]
    assert h[12] == rr["discount"]
    assert h[13] == rr["net"]
    assert h[16] == rr["hpp"]
    assert h[17] == rr["profit"]
    assert h[15] == h[13] + h[14]

# FK checks
assert all(r[1] <= len(dim_customer) for r in fact_sales)
assert all(r[2] <= len(dim_seller) for r in fact_sales)
assert all(r[3] <= len(dim_expedition) for r in fact_sales)
assert all(r[4] <= len(dim_payment) for r in fact_sales)
assert all(r[5] <= len(dim_date) for r in fact_sales)
assert all(r[5] <= len(dim_product) for r in fact_sales_item)

# ------------------------------------------------------------
# WRITE MART
# ------------------------------------------------------------
write_csv(MART/"dim_date.csv",
          ["date_key","full_date","day","month_number","month_name","quarter","year","iso_week","day_name","is_weekend"],
          dim_date)
write_csv(MART/"dim_customer.csv",
          ["customer_key","customer_id","customer_name","email","gender","join_date","street","city","province",
           "effective_from","effective_to","is_current"],
          dim_customer)
write_csv(MART/"dim_seller.csv",
          ["seller_key","seller_id","seller_name","seller_segment","street","city","province","join_date","seller_status"],
          dim_seller)
write_csv(MART/"dim_product.csv",
          ["product_key","product_id","product_name","brand","category","product_status"],
          dim_product)
write_csv(MART/"dim_ekspedisi.csv",
          ["expedition_key","expedition_code","expedition_name","base_shipping_fee","sla_days"],
          dim_expedition)
write_csv(MART/"dim_payment.csv",
          ["payment_key","payment_method_code","payment_method_name"],
          dim_payment)
write_csv(MART/"dim_order_status.csv",
          ["status_key","order_status","payment_status","shipment_status","promo_flag","bulk_order_flag","late_delivery_flag"],
          dim_order_status)
write_csv(MART/"fact_sales.csv",
          ["order_id","customer_key","seller_key","expedition_key","payment_key","order_date_key",
           "shipped_date_key","delivered_date_key","status_key","jumlah_item","total_quantity",
           "gross_subtotal","total_discount","net_product_sales","shipping_fee","grand_total",
           "total_hpp","profit","delivery_days"],
          fact_sales)
write_csv(MART/"fact_sales_item.csv",
          ["sales_item_key","order_item_id","order_id","customer_key","seller_key","product_key","order_date_key",
           "line_number","quantity","unit_price","unit_hpp","gross_subtotal","allocated_discount",
           "net_sales","total_hpp","profit"],
          fact_sales_item)

# ------------------------------------------------------------
# DOCUMENTATION
# ------------------------------------------------------------
mapping_rows = [
    ["raw_sources/customers.csv + customer_address_history.csv","datamart/dim_customer.csv","SCD Type 2 on customer address"],
    ["raw_sources/sellers.csv","datamart/dim_seller.csv","Surrogate key assigned"],
    ["raw_sources/products.csv","datamart/dim_product.csv","Surrogate key assigned; volatile price excluded from dimension"],
    ["raw_sources/expeditions.csv","datamart/dim_ekspedisi.csv","Reference master"],
    ["raw_sources/payment_methods.csv","datamart/dim_payment.csv","Reference master"],
    ["Calendar generator","datamart/dim_date.csv","Role-playing: order/shipped/delivered date keys"],
    ["orders + payments + shipments","datamart/dim_order_status.csv","Junk dimension combining low-cardinality status/flags"],
    ["orders + order_items + payments + shipments","datamart/fact_sales.csv","Grain: 1 row per order"],
    ["orders + order_items","datamart/fact_sales_item.csv","Grain: 1 row per product line within order"],
]
write_csv(DOCS/"source_to_mart_mapping.csv", ["source","target","transformation"], mapping_rows)

dict_rows = [
    ["table","column","type/role","description"],
    ["fact_sales","order_id","Degenerate dimension / PK","Business order identifier; one row per order"],
    ["fact_sales","customer_key","FK","Customer SCD2 surrogate key valid on order date"],
    ["fact_sales","seller_key","FK","Seller surrogate key"],
    ["fact_sales","expedition_key","FK","Expedition surrogate key"],
    ["fact_sales","payment_key","FK","Payment method surrogate key"],
    ["fact_sales","order_date_key","FK role-playing date","Order date"],
    ["fact_sales","shipped_date_key","FK role-playing date","Shipment date; nullable if not shipped"],
    ["fact_sales","delivered_date_key","FK role-playing date","Delivery date; nullable if not delivered"],
    ["fact_sales","status_key","FK / junk dimension","Combined order/payment/shipment statuses and flags"],
    ["fact_sales","jumlah_item","Additive count at order grain","Distinct product lines in order"],
    ["fact_sales","total_quantity","Additive","Total units in order"],
    ["fact_sales","gross_subtotal","Additive","Product value before discount, excluding shipping"],
    ["fact_sales","total_discount","Additive","Order discount"],
    ["fact_sales","net_product_sales","Additive","gross_subtotal - total_discount"],
    ["fact_sales","shipping_fee","Additive","Order-level shipping fee"],
    ["fact_sales","grand_total","Additive","net_product_sales + shipping_fee"],
    ["fact_sales","total_hpp","Additive","Total product cost"],
    ["fact_sales","profit","Additive","net_product_sales - total_hpp"],
    ["fact_sales","delivery_days","Non-additive","Days from shipped to delivered; aggregate using AVG/median"],
    ["fact_sales_item","sales_item_key","PK surrogate","Warehouse line-item key"],
    ["fact_sales_item","order_item_id","Degenerate identifier","Source line-item ID"],
    ["fact_sales_item","order_id","Degenerate dimension","Parent order identifier"],
    ["fact_sales_item","product_key","FK","Product dimension key"],
    ["fact_sales_item","quantity","Additive","Units purchased"],
    ["fact_sales_item","unit_price","Non-additive","Selling price per unit at transaction time"],
    ["fact_sales_item","unit_hpp","Non-additive","Unit cost at transaction time"],
    ["fact_sales_item","gross_subtotal","Additive","quantity × unit_price"],
    ["fact_sales_item","allocated_discount","Additive","Order discount allocated proportionally to line"],
    ["fact_sales_item","net_sales","Additive","gross_subtotal - allocated_discount"],
    ["fact_sales_item","total_hpp","Additive","quantity × unit_hpp"],
    ["fact_sales_item","profit","Additive","net_sales - total_hpp"],
    ["dim_customer","effective_from/effective_to/is_current","SCD Type 2","Preserves customer address history"],
]
write_csv(DOCS/"data_dictionary.csv", dict_rows[0], dict_rows[1:])

business_questions = """# Business Questions — Electronic Commerce

1. Seller yang berkontribusi paling besar terhadap profit?
2. Bagaimana tren jumlah order, net product sales, dan profit per bulan?
3. Apa provinsi yang mengasilkan profit paling tinggi?
4. Kategori produk apa yang banyak dijual pada saat weekend?
5. Pengiriman apa yang paling banyak digunakan di provinsi jawa tengah?

"""
(DOCS/"business_questions.md").write_text(business_questions, encoding="utf-8")

readme = f"""# Synthetic E-Commerce Dataset — DWBI 2026

Dataset ini dibuat untuk domain **Electronic Commerce** dan mengikuti kebutuhan proyek
Dimensional Modeling / Data Mart.

## Lapisan 1 — Raw Sources
Data mentah menyerupai sumber operasional:
- customers.csv
- customer_address_history.csv
- sellers.csv
- products.csv
- product_price_history.csv
- orders.csv (**20,000 order/transaksi**)
- order_items.csv (**{len(order_items):,} item lines**)
- payments.csv
- shipments.csv
- expeditions.csv
- payment_methods.csv

## Lapisan 2 — Data Mart
- dim_customer.csv — SCD Type 2
- dim_seller.csv
- dim_product.csv
- dim_ekspedisi.csv
- dim_payment.csv
- dim_date.csv
- dim_order_status.csv — junk dimension
- fact_sales.csv — grain: **1 row = 1 order**, exactly **20,000 rows**
- fact_sales_item.csv — grain: **1 row = 1 product line in an order**, **{len(fact_sales_item):,} rows**

## Scenario Coverage
- Multiple items in one order
- 20,000 transactions
- Payment success/failure/pending/refund
- Shipment delivered/in-transit/not-shipped/returned
- Late-delivery scenario
- Promotions and order-level discounts
- Bulk/high-value outliers
- Product price/HPP history
- Customer address changes used to create SCD Type 2
- Role-playing date dimension: order / shipped / delivered date
- Junk dimension for low-cardinality statuses and flags

## Core Reconciliation
For every order:
- gross_subtotal = SUM(fact_sales_item.gross_subtotal)
- total_discount = SUM(fact_sales_item.allocated_discount)
- net_product_sales = SUM(fact_sales_item.net_sales)
- total_hpp = SUM(fact_sales_item.total_hpp)
- profit = SUM(fact_sales_item.profit)
- grand_total = net_product_sales + shipping_fee

## Seed
{SEED}

## DuckDB (Colab-ready)
Script versi Colab juga membuat database analitik:
- `ecommerce_dwbi.duckdb`
- seluruh CSV pada folder `datamart/` dimuat menjadi tabel fisik DuckDB
- contoh query analitik tersedia di `scripts/analytic_queries_duckdb.sql`
- hasil query otomatis disimpan di folder `query_results/`
"""
(DOCS/"README.md").write_text(readme, encoding="utf-8")

# ------------------------------------------------------------
# SQL DDL
# ------------------------------------------------------------
ddl = r"""
-- Data Mart DDL - PostgreSQL
DROP TABLE IF EXISTS fact_sales_item;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_order_status;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_seller;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_ekspedisi;
DROP TABLE IF EXISTS dim_payment;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
  date_key INT PRIMARY KEY,
  full_date DATE NOT NULL UNIQUE,
  day INT, month_number INT, month_name VARCHAR(15),
  quarter INT, year INT, iso_week INT, day_name VARCHAR(15), is_weekend CHAR(1)
);

CREATE TABLE dim_customer (
  customer_key INT PRIMARY KEY,
  customer_id VARCHAR(20) NOT NULL,
  customer_name VARCHAR(120), email VARCHAR(160), gender CHAR(1), join_date DATE,
  street VARCHAR(160), city VARCHAR(80), province VARCHAR(80),
  effective_from DATE NOT NULL, effective_to DATE NOT NULL, is_current CHAR(1) NOT NULL
);

CREATE TABLE dim_seller (
  seller_key INT PRIMARY KEY,
  seller_id VARCHAR(20) UNIQUE NOT NULL,
  seller_name VARCHAR(140), seller_segment VARCHAR(30),
  street VARCHAR(160), city VARCHAR(80), province VARCHAR(80),
  join_date DATE, seller_status VARCHAR(20)
);

CREATE TABLE dim_product (
  product_key INT PRIMARY KEY,
  product_id VARCHAR(20) UNIQUE NOT NULL,
  product_name VARCHAR(180), brand VARCHAR(80), category VARCHAR(80), product_status VARCHAR(20)
);

CREATE TABLE dim_ekspedisi (
  expedition_key INT PRIMARY KEY,
  expedition_code VARCHAR(20) UNIQUE NOT NULL,
  expedition_name VARCHAR(120), base_shipping_fee BIGINT, sla_days INT
);

CREATE TABLE dim_payment (
  payment_key INT PRIMARY KEY,
  payment_method_code VARCHAR(20) UNIQUE NOT NULL,
  payment_method_name VARCHAR(80)
);

CREATE TABLE dim_order_status (
  status_key INT PRIMARY KEY,
  order_status VARCHAR(20), payment_status VARCHAR(20), shipment_status VARCHAR(20),
  promo_flag CHAR(1), bulk_order_flag CHAR(1), late_delivery_flag CHAR(1)
);

CREATE TABLE fact_sales (
  order_id VARCHAR(20) PRIMARY KEY,
  customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
  seller_key INT NOT NULL REFERENCES dim_seller(seller_key),
  expedition_key INT NOT NULL REFERENCES dim_ekspedisi(expedition_key),
  payment_key INT NOT NULL REFERENCES dim_payment(payment_key),
  order_date_key INT NOT NULL REFERENCES dim_date(date_key),
  shipped_date_key INT REFERENCES dim_date(date_key),
  delivered_date_key INT REFERENCES dim_date(date_key),
  status_key INT NOT NULL REFERENCES dim_order_status(status_key),
  jumlah_item INT NOT NULL,
  total_quantity INT NOT NULL,
  gross_subtotal BIGINT NOT NULL,
  total_discount BIGINT NOT NULL,
  net_product_sales BIGINT NOT NULL,
  shipping_fee BIGINT NOT NULL,
  grand_total BIGINT NOT NULL,
  total_hpp BIGINT NOT NULL,
  profit BIGINT NOT NULL,
  delivery_days INT
);

CREATE TABLE fact_sales_item (
  sales_item_key BIGINT PRIMARY KEY,
  order_item_id VARCHAR(24) UNIQUE NOT NULL,
  order_id VARCHAR(20) NOT NULL,
  customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
  seller_key INT NOT NULL REFERENCES dim_seller(seller_key),
  product_key INT NOT NULL REFERENCES dim_product(product_key),
  order_date_key INT NOT NULL REFERENCES dim_date(date_key),
  line_number INT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price BIGINT NOT NULL,
  unit_hpp BIGINT NOT NULL,
  gross_subtotal BIGINT NOT NULL,
  allocated_discount BIGINT NOT NULL,
  net_sales BIGINT NOT NULL,
  total_hpp BIGINT NOT NULL,
  profit BIGINT NOT NULL,
  UNIQUE(order_id, line_number)
);

CREATE INDEX idx_fact_sales_date ON fact_sales(order_date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_seller ON fact_sales(seller_key);
CREATE INDEX idx_fact_sales_status ON fact_sales(status_key);
CREATE INDEX idx_fact_sales_item_product ON fact_sales_item(product_key);
CREATE INDEX idx_fact_sales_item_order ON fact_sales_item(order_id);
"""
(SCRIPTS/"create_datamart_postgresql.sql").write_text(ddl.strip()+"\n", encoding="utf-8")

# ------------------------------------------------------------
# VALIDATION REPORT
# ------------------------------------------------------------
completed = sum(1 for o in orders if o[4] == "COMPLETED")
bulk = sum(1 for o in orders if o[12])
high_value = sum(1 for o in orders if o[13] == "HIGH_VALUE")
late = sum(1 for s in shipments if s[8] == "Y")
customer_scd_count = sum(1 for cid in customer_ids if len(customer_versions[cid]) > 1)

validation = {
    "seed": SEED,
    "orders": len(orders),
    "order_items": len(order_items),
    "completed_orders": completed,
    "bulk_orders": bulk,
    "high_value_orders": high_value,
    "late_deliveries": late,
    "customers_with_scd2_history": customer_scd_count,
    "dim_customer_rows": len(dim_customer),
    "dim_order_status_rows": len(dim_order_status),
    "fact_sales_rows": len(fact_sales),
    "fact_sales_item_rows": len(fact_sales_item),
    "referential_integrity": "PASS",
    "header_item_reconciliation": "PASS"
}
(DOCS/"validation_summary.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")

# ------------------------------------------------------------
# DUCKDB ANALYTICS (COLAB-READY)
# ------------------------------------------------------------
# The queries below use ONLY the dimensional data mart, not the raw layer.
# Revenue is represented by net_product_sales; GMV by grand_total.
DUCKDB_QUERIES = {
    "q1": """
        SELECT
            s.seller_id,
            s.seller_name,
            COUNT(f.order_id) AS total_orders,
            SUM(f.net_product_sales) AS revenue,
            SUM(f.profit) AS profit
        FROM fact_sales f
        JOIN dim_seller s ON f.seller_key = s.seller_key
        JOIN dim_order_status st ON f.status_key = st.status_key
        WHERE st.order_status = 'COMPLETED'
        GROUP BY s.seller_name,s.seller_id
        ORDER BY profit DESC LIMIT 5
    """,

    "q2": """
        SELECT
            d.year,
            d.month_number,
            d.month_name,
            COUNT(*) AS total_orders,
            SUM(f.net_product_sales)/1000000000 AS net_product_sales_miliar,
            SUM(f.profit)/1000000 AS profit_juta,
        FROM fact_sales f
        JOIN dim_date d ON f.order_date_key = d.date_key
        JOIN dim_order_status st ON f.status_key = st.status_key
        WHERE st.order_status <> 'CANCELLED'
        GROUP BY d.year, d.month_number, d.month_name
        ORDER BY d.year, d.month_number
    """,

    "q3": """
        SELECT 
            c.province AS customer_province,
            COUNT(f.order_id) AS total_orders,
            SUM(f.net_product_sales)/ 1000000.0 AS revenue_juta,
            SUM(f.profit) / 1000000.0 AS profit_juta
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_order_status st ON f.status_key = st.status_key
        WHERE st.order_status = 'COMPLETED'
        GROUP BY c.province
        ORDER BY profit_juta DESC
    """,

    "q4": """
        SELECT
            p.category,
            SUM(i.quantity) AS units_sold,
            SUM(i.net_sales) / 1000000000.0 AS net_sales_miliar,
            SUM(i.profit) / 1000000000.0 AS profit_miliar
        FROM fact_sales_item i
        JOIN dim_product p ON i.product_key = p.product_key
        JOIN fact_sales f ON i.order_id = f.order_id
        JOIN dim_order_status st ON f.status_key = st.status_key
        JOIN dim_date d ON f.order_date_key = d.date_key
        WHERE st.order_status = 'COMPLETED'
          AND d.is_weekend = 'Y'
        GROUP BY p.category
        ORDER BY units_sold DESC
    """,

    "q5": """
        SELECT
                e.expedition_code,
                e.expedition_name,
                COUNT(DISTINCT f.order_id) AS total_orders
        FROM fact_sales f
        JOIN dim_customer c
                ON f.customer_key = c.customer_key
        JOIN dim_ekspedisi e
                ON f.expedition_key = e.expedition_key
        JOIN dim_order_status st
                ON f.status_key = st.status_key
        WHERE st.order_status = 'COMPLETED'
              AND UPPER(TRIM(c.province)) = 'JAWA TENGAH'
        GROUP BY
                e.expedition_code,
                e.expedition_name
        ORDER BY total_orders DESC
    """
}

query_sql_text = "-- DuckDB analytic queries generated by generate_dataset_colab_duckdb.py\n\n"
for query_name, query_sql in DUCKDB_QUERIES.items():
    query_sql_text += f"-- {query_name}\n{query_sql.strip()};\n\n"
(SCRIPTS / "analytic_queries_duckdb.sql").write_text(query_sql_text, encoding="utf-8")


def _sql_path(path: Path) -> str:
    """Return a safely quoted POSIX path for SQL string literals."""
    return path.resolve().as_posix().replace("'", "''")


def ensure_duckdb():
    """Import DuckDB; install it automatically when running in Colab if needed."""
    try:
        import duckdb
        return duckdb
    except ImportError:
        if os.environ.get("DWBI_AUTO_INSTALL_DUCKDB", "1") != "1":
            raise
        print("DuckDB belum terpasang. Installing package 'duckdb'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "duckdb"])
        import duckdb
        return duckdb


def build_duckdb_from_datamart():
    duckdb = ensure_duckdb()
    con = duckdb.connect(str(DUCKDB_PATH))

    table_files = {
        "dim_date": MART / "dim_date.csv",
        "dim_customer": MART / "dim_customer.csv",
        "dim_seller": MART / "dim_seller.csv",
        "dim_product": MART / "dim_product.csv",
        "dim_ekspedisi": MART / "dim_ekspedisi.csv",
        "dim_payment": MART / "dim_payment.csv",
        "dim_order_status": MART / "dim_order_status.csv",
        "fact_sales": MART / "fact_sales.csv",
        "fact_sales_item": MART / "fact_sales_item.csv",
    }

    # Load CSV mart files as physical DuckDB tables. sample_size=-1 scans the
    # complete file for type inference, which is safer for nullable date keys.
    for table_name, csv_path in table_files.items():
        csv_sql_path = _sql_path(csv_path)
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT *
            FROM read_csv_auto(
                '{csv_sql_path}',
                header = true,
                sample_size = -1,
                nullstr = ''
            )
        """)

    con.execute("ANALYZE")

    # Sanity checks from the data mart inside DuckDB.
    mart_counts = {}
    for table_name in table_files:
        mart_counts[table_name] = con.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

    if mart_counts["fact_sales"] != N_ORDERS:
        raise AssertionError(
            f"DuckDB fact_sales expected {N_ORDERS} rows, found {mart_counts['fact_sales']}"
        )
    if mart_counts["fact_sales_item"] != len(fact_sales_item):
        raise AssertionError(
            "DuckDB fact_sales_item row count does not match generated mart"
        )

    # Run sample analytical queries and save each result as CSV.
    query_result_rows = {}
    for query_name, query_sql in DUCKDB_QUERIES.items():
        result_path = QUERY_RESULTS / f"{query_name}.csv"
        copy_sql = query_sql.strip().rstrip(";")
        con.execute(
            f"COPY ({copy_sql}) TO '{_sql_path(result_path)}' "
            "(HEADER, DELIMITER ',')"
        )
        query_result_rows[query_name] = con.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{_sql_path(result_path)}', header=true)"
        ).fetchone()[0]

    # Create a convenient semantic view for interactive Colab analysis.
    con.execute("DROP VIEW IF EXISTS vw_sales_enriched")
    con.execute("""
        CREATE VIEW vw_sales_enriched AS
        SELECT
            f.*,
            d.full_date,
            d.year,
            d.month_number,
            d.month_name,
            d.day,
            d.day_name,
            d.is_weekend,
            c.customer_id,
            c.customer_name,
            c.city AS customer_city,
            c.province AS customer_province,
            s.seller_id,
            s.seller_name,
            s.city AS seller_city,
            s.province AS seller_province,
            e.expedition_name,
            p.payment_method_name,
            st.order_status,
            st.payment_status,
            st.shipment_status,
            st.promo_flag,
            st.bulk_order_flag,
            st.late_delivery_flag
        FROM fact_sales f
        JOIN dim_date d ON f.order_date_key = d.date_key
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_seller s ON f.seller_key = s.seller_key
        JOIN dim_ekspedisi e ON f.expedition_key = e.expedition_key
        JOIN dim_payment p ON f.payment_key = p.payment_key
        JOIN dim_order_status st ON f.status_key = st.status_key
    """)

    con.close()
    return mart_counts, query_result_rows


DUCKDB_ENABLED = os.environ.get("DWBI_ENABLE_DUCKDB", "1") == "1"
if DUCKDB_ENABLED:
    duckdb_counts, duckdb_query_rows = build_duckdb_from_datamart()
    validation["duckdb_database"] = str(DUCKDB_PATH)
    validation["duckdb_table_counts"] = duckdb_counts
    validation["duckdb_query_result_rows"] = duckdb_query_rows
    validation["duckdb_status"] = "PASS"
else:
    validation["duckdb_status"] = "SKIPPED (DWBI_ENABLE_DUCKDB=0)"

# Rewrite validation summary after DuckDB validation.
(DOCS/"validation_summary.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")

# ------------------------------------------------------------
# ZIP FINAL PROJECT
# ------------------------------------------------------------
# Close the database before zipping to avoid partially flushed files.
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for path in ROOT.rglob("*"):
        if path.is_file():
            z.write(path, arcname=str(path.relative_to(ROOT)))

print("\n=== VALIDATION SUMMARY ===")
print(json.dumps(validation, indent=2))
print("\nDuckDB :", DUCKDB_PATH)
print("Queries:", SCRIPTS / "analytic_queries_duckdb.sql")
print("Results:", QUERY_RESULTS)
print("ZIP    :", ZIP_PATH)
