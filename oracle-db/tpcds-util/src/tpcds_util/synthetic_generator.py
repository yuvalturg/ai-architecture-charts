"""Synthetic data generation for TPC-DS schema with realistic patterns."""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Try to import Faker, fall back to basic generation if not available
try:
    from faker import Faker
    from faker.providers import address, automotive, company, internet, person

    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class DataGenerationConfig:
    """Configuration for synthetic data generation."""

    scale_factor: int = 1
    start_date: date = date(2020, 1, 1)
    end_date: date = date(2023, 12, 31)
    num_customers: int = 100000
    num_items: int = 18000
    num_stores: int = 12
    num_warehouses: int = 5
    num_web_sites: int = 30
    num_call_centers: int = 8
    seasonal_variance: float = 0.3  # 30% seasonal variation
    weekend_boost: float = 1.2  # 20% higher sales on weekends


class SyntheticDataGenerator:
    """Generates realistic synthetic data for TPC-DS schema."""

    def __init__(self, config: DataGenerationConfig):
        self.config = config
        self.fake = Faker() if HAS_FAKER else None
        if self.fake:
            self.fake.add_provider(automotive)
            self.fake.add_provider(company)
            self.fake.add_provider(internet)
            self.fake.add_provider(address)
            self.fake.add_provider(person)

        # Pre-generate lookup data for consistency
        self._initialize_lookups()

        # Data caches for referential integrity
        self.generated_data = {}
        self.dimension_keys = {}

    def _initialize_lookups(self):
        """Initialize lookup tables for consistent data generation."""

        # Product categories with realistic relationships
        self.product_categories = {
            "Electronics": ["Computers", "Phones", "Audio", "Gaming", "Accessories"],
            "Clothing": ["Men", "Women", "Children", "Shoes", "Accessories"],
            "Home & Garden": ["Furniture", "Kitchen", "Bedroom", "Garden", "Tools"],
            "Sports": [
                "Fitness",
                "Outdoor",
                "Team Sports",
                "Water Sports",
                "Winter Sports",
            ],
            "Books": ["Fiction", "Non-Fiction", "Educational", "Children", "Reference"],
            "Automotive": ["Parts", "Accessories", "Tools", "Care", "Electronics"],
        }

        # Brand names for different categories
        self.brands = {
            "Electronics": [
                "TechCorp",
                "DigitalPlus",
                "InnovateTech",
                "PowerElectronics",
                "SmartDevices",
            ],
            "Clothing": [
                "StyleMax",
                "FashionForward",
                "ComfortWear",
                "UrbanStyle",
                "ClassicFit",
            ],
            "Home & Garden": [
                "HomeComfort",
                "LivingSpace",
                "CozyHome",
                "ModernLiving",
                "GardenPro",
            ],
            "Sports": [
                "ActiveLife",
                "SportsPro",
                "FitnessFlex",
                "OutdoorAdventure",
                "TeamSpirit",
            ],
            "Books": [
                "KnowledgePress",
                "StoryBooks",
                "LearnMore",
                "ReadWell",
                "BookCraft",
            ],
            "Automotive": [
                "AutoPro",
                "CarCare",
                "DriveSmart",
                "VehiclePlus",
                "MotorMax",
            ],
        }

        # Geographic regions with realistic state clusters
        self.regions = {
            "West": ["CA", "WA", "OR", "NV", "AZ", "UT", "CO", "ID", "MT", "WY"],
            "East": ["NY", "NJ", "PA", "CT", "MA", "ME", "VT", "NH", "RI"],
            "South": [
                "TX",
                "FL",
                "GA",
                "NC",
                "SC",
                "VA",
                "TN",
                "AL",
                "MS",
                "LA",
                "AR",
                "OK",
            ],
            "Midwest": [
                "IL",
                "IN",
                "OH",
                "MI",
                "WI",
                "MN",
                "IA",
                "MO",
                "ND",
                "SD",
                "NE",
                "KS",
            ],
        }

        # Income levels with realistic distributions
        self.income_bands = [
            ("[0-10K)", 0.08),  # 8% low income
            ("[10-20K)", 0.12),  # 12% lower income
            ("[20-30K)", 0.15),  # 15% lower-middle
            ("[30-50K)", 0.25),  # 25% middle
            ("[50-75K)", 0.20),  # 20% upper-middle
            ("[75-100K)", 0.12),  # 12% upper
            ("[100K+)", 0.08),  # 8% high income
        ]

        # Seasonal patterns for different product categories
        self.seasonal_patterns = {
            "Electronics": {
                1: 0.8,
                2: 0.9,
                3: 1.0,
                4: 1.0,
                5: 1.0,
                6: 1.1,
                7: 1.1,
                8: 1.0,
                9: 1.0,
                10: 1.1,
                11: 1.3,
                12: 1.8,
            },
            "Clothing": {
                1: 0.7,
                2: 0.8,
                3: 1.2,
                4: 1.3,
                5: 1.1,
                6: 1.0,
                7: 0.9,
                8: 1.0,
                9: 1.2,
                10: 1.1,
                11: 1.4,
                12: 1.6,
            },
            "Home & Garden": {
                1: 0.8,
                2: 0.9,
                3: 1.3,
                4: 1.4,
                5: 1.3,
                6: 1.1,
                7: 1.0,
                8: 1.0,
                9: 1.1,
                10: 1.0,
                11: 1.1,
                12: 1.2,
            },
            "Sports": {
                1: 1.2,
                2: 1.1,
                3: 1.2,
                4: 1.3,
                5: 1.4,
                6: 1.3,
                7: 1.2,
                8: 1.1,
                9: 1.2,
                10: 1.1,
                11: 1.0,
                12: 1.3,
            },
        }

    def _get_weighted_choice(self, choices: List[Tuple[str, float]]) -> str:
        """Select a weighted random choice."""
        weights = [weight for _, weight in choices]
        return random.choices([choice for choice, _ in choices], weights=weights)[0]

    def _generate_realistic_name(self, name_type: str = "company") -> str:
        """Generate realistic names using Faker or fallback."""
        if self.fake:
            if name_type == "company":
                return self.fake.company()
            elif name_type == "person_first":
                return self.fake.first_name()
            elif name_type == "person_last":
                return self.fake.last_name()
            elif name_type == "address":
                return self.fake.street_address()
            elif name_type == "city":
                return self.fake.city()

        # Fallback to pre-defined realistic options
        fallbacks = {
            "company": [
                "MegaCorp Inc",
                "Global Solutions LLC",
                "Premier Services",
                "Advanced Systems",
            ],
            "person_first": [
                "John",
                "Mary",
                "David",
                "Sarah",
                "Michael",
                "Lisa",
                "Robert",
                "Jennifer",
            ],
            "person_last": [
                "Smith",
                "Johnson",
                "Williams",
                "Brown",
                "Jones",
                "Garcia",
                "Miller",
                "Davis",
            ],
            "city": [
                "Springfield",
                "Riverside",
                "Franklin",
                "Georgetown",
                "Madison",
                "Oak Hill",
            ],
        }
        return random.choice(fallbacks.get(name_type, ["Default"]))

    def generate_date_dimension(self) -> List[Dict]:
        """Generate comprehensive date dimension with realistic patterns."""
        dates = []
        current_date = self.config.start_date

        while current_date <= self.config.end_date:
            # Calculate various date attributes
            week_seq = (current_date - self.config.start_date).days // 7
            month_seq = (
                current_date.year - self.config.start_date.year
            ) * 12 + current_date.month
            quarter_seq = (
                (current_date.year - self.config.start_date.year) * 4
                + ((current_date.month - 1) // 3)
                + 1
            )

            # Determine if it's a holiday (simplified)
            is_holiday = (
                "Y"
                if (
                    (current_date.month == 12 and current_date.day in [24, 25, 31])
                    or (current_date.month == 1 and current_date.day == 1)
                    or (current_date.month == 7 and current_date.day == 4)
                    or (
                        current_date.month == 11
                        and 22 <= current_date.day <= 28
                        and current_date.weekday() == 3
                    )  # Thanksgiving
                )
                else "N"
            )

            date_record = {
                "d_date_sk": len(dates) + 1,
                "d_date_id": current_date.strftime("%Y-%m-%d"),
                "d_date": current_date,
                "d_month_seq": month_seq,
                "d_week_seq": week_seq,
                "d_quarter_seq": quarter_seq,
                "d_year": current_date.year,
                "d_dow": current_date.weekday() + 1,  # 1=Monday, 7=Sunday
                "d_moy": current_date.month,
                "d_dom": current_date.day,
                "d_qoy": ((current_date.month - 1) // 3) + 1,
                "d_fy_year": (
                    current_date.year
                    if current_date.month >= 7
                    else current_date.year - 1
                ),
                "d_fy_quarter_seq": quarter_seq,
                "d_fy_week_seq": week_seq,
                "d_day_name": current_date.strftime("%A"),
                "d_quarter_name": f"Q{((current_date.month - 1) // 3) + 1}",
                "d_holiday": is_holiday,
                "d_weekend": "Y" if current_date.weekday() >= 5 else "N",
                "d_following_holiday": "N",  # Simplified
                "d_first_dom": 1,
                "d_last_dom": (
                    current_date.replace(month=current_date.month % 12 + 1, day=1)
                    - timedelta(days=1)
                ).day,
                "d_same_day_ly": (
                    (current_date - timedelta(days=365)).toordinal()
                    if current_date >= self.config.start_date + timedelta(days=365)
                    else None
                ),
                "d_same_day_lq": (
                    (current_date - timedelta(days=90)).toordinal()
                    if current_date >= self.config.start_date + timedelta(days=90)
                    else None
                ),
                "d_current_day": "Y" if current_date == date.today() else "N",
                "d_current_week": "N",  # Simplified
                "d_current_month": (
                    "Y"
                    if current_date.year == date.today().year
                    and current_date.month == date.today().month
                    else "N"
                ),
                "d_current_quarter": "N",  # Simplified
                "d_current_year": (
                    "Y" if current_date.year == date.today().year else "N"
                ),
            }

            dates.append(date_record)
            current_date += timedelta(days=1)

        self.generated_data["date_dim"] = dates
        self.dimension_keys["date_dim"] = [d["d_date_sk"] for d in dates]
        return dates

    def generate_customer_demographics(self) -> List[Dict]:
        """Generate realistic customer demographics."""
        demographics = []

        for i in range(10000):  # Standard demographic segments
            demo_sk = i + 1

            # Generate realistic demographic combinations
            gender = random.choice(["M", "F"])
            marital_status = random.choice(
                ["S", "M", "W", "D"]
            )  # Single, Married, Widowed, Divorced
            education_levels = [
                "Primary",
                "Secondary",
                "College",
                "Advanced Degree",
                "Unknown",
            ]
            education = random.choice(education_levels)

            # Purchase estimate based on education and other factors
            base_purchase = 500
            if education == "Advanced Degree":
                base_purchase *= 2.5
            elif education == "College":
                base_purchase *= 1.8
            elif education == "Secondary":
                base_purchase *= 1.2

            purchase_estimate = int(base_purchase * random.uniform(0.5, 2.0))

            # Credit rating correlated with purchase estimate
            if purchase_estimate > 2000:
                credit_rating = random.choice(["Good", "High Risk", "Low Risk"])
            else:
                credit_rating = random.choice(["Good", "High Risk", "Unknown"])

            # Dependents
            dep_count = random.choices(
                [0, 1, 2, 3, 4, 5], weights=[20, 25, 30, 15, 8, 2]
            )[0]
            dep_employed = (
                min(dep_count, random.randint(0, dep_count)) if dep_count > 0 else 0
            )
            dep_college = (
                min(dep_count, random.randint(0, dep_count // 2))
                if dep_count > 0
                else 0
            )

            demo_record = {
                "cd_demo_sk": demo_sk,
                "cd_gender": gender,
                "cd_marital_status": marital_status,
                "cd_education_status": education,
                "cd_purchase_estimate": purchase_estimate,
                "cd_credit_rating": credit_rating,
                "cd_dep_count": dep_count,
                "cd_dep_employed_count": dep_employed,
                "cd_dep_college_count": dep_college,
            }

            demographics.append(demo_record)

        self.generated_data["customer_demographics"] = demographics
        self.dimension_keys["customer_demographics"] = [
            d["cd_demo_sk"] for d in demographics
        ]
        return demographics

    def generate_customer_addresses(self) -> List[Dict]:
        """Generate realistic customer addresses with geographic clustering."""
        addresses = []

        # Generate addresses clustered by regions
        for region, states in self.regions.items():
            addresses_per_region = (
                self.config.num_customers // 4
            )  # Divide among 4 regions

            for i in range(addresses_per_region):
                address_sk = len(addresses) + 1
                state = random.choice(states)

                address_record = {
                    "ca_address_sk": address_sk,
                    "ca_address_id": f"ADDR{address_sk:010d}",
                    "ca_street_number": str(random.randint(1, 9999)),
                    "ca_street_name": self._generate_realistic_name("address"),
                    "ca_street_type": random.choice(
                        ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way"]
                    ),
                    "ca_suite_number": (
                        f"Suite {random.randint(1, 200)}"
                        if random.random() < 0.3
                        else None
                    ),
                    "ca_city": self._generate_realistic_name("city"),
                    "ca_county": f'{self._generate_realistic_name("city")[:15]} Co',  # Shortened to fit 30 char limit
                    "ca_state": state,
                    "ca_zip": f"{random.randint(10000, 99999)}",
                    "ca_country": "United States",
                    "ca_gmt_offset": self._get_gmt_offset(state),
                    "ca_location_type": random.choice(
                        ["apartment", "condo", "single family", "unknown"]
                    ),
                }

                addresses.append(address_record)

        self.generated_data["customer_address"] = addresses
        self.dimension_keys["customer_address"] = [
            a["ca_address_sk"] for a in addresses
        ]
        return addresses

    def generate_warehouses(self) -> List[Dict]:
        """Generate realistic warehouse data."""
        warehouses = []

        for i in range(self.config.num_warehouses):
            warehouse_sk = i + 1

            # Distribute warehouses across regions for realistic coverage
            region_name = list(self.regions.keys())[i % len(self.regions)]
            state = random.choice(self.regions[region_name])

            warehouse_record = {
                "w_warehouse_sk": warehouse_sk,
                "w_warehouse_id": f"WARE{warehouse_sk:010d}",
                "w_warehouse_name": f"{region_name} DC{warehouse_sk}",  # Shortened to fit 20 char limit
                "w_warehouse_sq_ft": random.randint(50000, 500000),  # 50K to 500K sq ft
                "w_street_number": str(random.randint(1, 9999)),
                "w_street_name": self._generate_realistic_name("address"),
                "w_street_type": random.choice(["St", "Ave", "Blvd", "Way", "Dr"]),
                "w_suite_number": (
                    f"Bldg {random.randint(1, 20)}" if random.random() < 0.4 else None
                ),
                "w_city": self._generate_realistic_name("city"),
                "w_county": f'{self._generate_realistic_name("city")} County',
                "w_state": state,
                "w_zip": f"{random.randint(10000, 99999)}",
                "w_country": "United States",
                "w_gmt_offset": self._get_gmt_offset(state),
            }

            warehouses.append(warehouse_record)

        self.generated_data["warehouse"] = warehouses
        self.dimension_keys["warehouse"] = [w["w_warehouse_sk"] for w in warehouses]
        return warehouses

    def generate_stores(self) -> List[Dict]:
        """Generate realistic store data with geographic distribution."""
        stores = []

        for i in range(self.config.num_stores):
            store_sk = i + 1

            # Distribute stores across regions
            region_name = list(self.regions.keys())[i % len(self.regions)]
            state = random.choice(self.regions[region_name])

            # Store types with realistic attributes
            store_types = [
                ("Superstore", 80000, 200),
                ("Department Store", 50000, 150),
                ("Specialty Store", 15000, 50),
                ("Outlet Store", 25000, 75),
            ]
            store_type, sq_ft, employee_count = random.choice(store_types)

            store_record = {
                "s_store_sk": store_sk,
                "s_store_id": f"STORE{store_sk:010d}",
                "s_rec_start_date": self.config.start_date,
                "s_rec_end_date": None,
                "s_closed_date_sk": None,
                "s_store_name": f"{region_name} {store_type} #{store_sk}",
                "s_number_employees": employee_count + random.randint(-20, 20),
                "s_floor_space": sq_ft + random.randint(-5000, 5000),
                "s_hours": "M-Sa 8AM-10PM Su 10-8"[:20],  # Ensure 20 char limit
                "s_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                "s_market_id": (i % 10) + 1,  # 10 market regions
                "s_geography_class": random.choice(["Urban", "Suburban", "Rural"]),
                "s_market_desc": f"{region_name} Market Region",
                "s_market_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                "s_division_id": (i % 3) + 1,  # 3 divisions
                "s_division_name": random.choice(
                    ["North Division", "South Division", "Central Division"]
                ),
                "s_company_id": 1,  # Single company
                "s_company_name": "RetailCorp",
                "s_street_number": str(random.randint(1, 9999)),
                "s_street_name": self._generate_realistic_name("address"),
                "s_street_type": random.choice(["St", "Ave", "Blvd", "Way"]),
                "s_suite_number": (
                    f"Suite {random.randint(1, 50)}" if random.random() < 0.2 else None
                ),
                "s_city": self._generate_realistic_name("city"),
                "s_county": f'{self._generate_realistic_name("city")} County',
                "s_state": state,
                "s_zip": f"{random.randint(10000, 99999)}",
                "s_country": "United States",
                "s_gmt_offset": self._get_gmt_offset(state),
                "s_tax_precentage": round(random.uniform(0.05, 0.12), 4),  # 5-12% tax
            }

            stores.append(store_record)

        self.generated_data["store"] = stores
        self.dimension_keys["store"] = [s["s_store_sk"] for s in stores]
        return stores

    def generate_items(self) -> List[Dict]:
        """Generate realistic product items with categories and pricing."""
        items = []

        for i in range(self.config.num_items):
            item_sk = i + 1

            # Select category and subcategory
            category = random.choice(list(self.product_categories.keys()))
            subcategory = random.choice(self.product_categories[category])
            brand = random.choice(self.brands[category])

            # Generate realistic pricing based on category
            price_ranges = {
                "Electronics": (20, 2000),
                "Clothing": (15, 300),
                "Home & Garden": (10, 1500),
                "Sports": (25, 800),
                "Books": (8, 100),
                "Automotive": (15, 500),
            }
            min_price, max_price = price_ranges[category]
            current_price = round(random.uniform(min_price, max_price), 2)
            wholesale_cost = round(
                current_price * random.uniform(0.4, 0.7), 2
            )  # 40-70% of retail

            # Product attributes
            colors = [
                "red",
                "blue",
                "green",
                "black",
                "white",
                "gray",
                "brown",
                "yellow",
                "purple",
                "orange",
            ]
            sizes = ["XS", "S", "M", "L", "XL", "XXL", "OS"]  # OS = One Size

            item_record = {
                "i_item_sk": item_sk,
                "i_item_id": f"ITEM{item_sk:010d}",
                "i_rec_start_date": self.config.start_date,
                "i_rec_end_date": None,
                "i_item_desc": f"{brand} {subcategory} Product {item_sk}",
                "i_current_price": current_price,
                "i_wholesale_cost": wholesale_cost,
                "i_brand_id": hash(brand) % 1000 + 1,
                "i_brand": brand,
                "i_class_id": hash(subcategory) % 100 + 1,
                "i_class": subcategory,
                "i_category_id": hash(category) % 50 + 1,
                "i_category": category,
                "i_manufact_id": random.randint(1, 1000),
                "i_manufact": f"{brand} Manufacturing",
                "i_size": random.choice(sizes) if category == "Clothing" else "OS",
                "i_formulation": f"Formula-{random.randint(1, 100)}",
                "i_color": random.choice(colors),
                "i_units": random.choice(["Each", "Pair", "Set", "Dozen", "Case"]),
                "i_container": random.choice(
                    ["Box", "Bag", "Case", "Carton", "Package"]
                ),
                "i_manager_id": random.randint(1, 100),
                "i_product_name": f"{brand} {subcategory}",
            }

            items.append(item_record)

        self.generated_data["item"] = items
        self.dimension_keys["item"] = [i["i_item_sk"] for i in items]
        return items

    def generate_customers(self) -> List[Dict]:
        """Generate realistic customer data with demographics and addresses."""
        customers = []

        # Ensure we have addresses and demographics
        if "customer_address" not in self.generated_data:
            self.generate_customer_addresses()
        if "customer_demographics" not in self.generated_data:
            self.generate_customer_demographics()

        for i in range(self.config.num_customers):
            customer_sk = i + 1

            # Link to demographics and address
            demo_sk = random.choice(self.dimension_keys["customer_demographics"])
            address_sk = random.choice(self.dimension_keys["customer_address"])

            # Generate realistic customer info
            first_name = self._generate_realistic_name("person_first")
            last_name = self._generate_realistic_name("person_last")
            birth_year = random.randint(1940, 2005)  # Ages 18-83

            customer_record = {
                "c_customer_sk": customer_sk,
                "c_customer_id": f"CUST{customer_sk:010d}",
                "c_current_cdemo_sk": demo_sk,
                "c_current_hdemo_sk": random.randint(1, 7200),  # Household demographics
                "c_current_addr_sk": address_sk,
                "c_first_shipto_date_sk": random.choice(
                    self.dimension_keys["date_dim"]
                ),
                "c_first_sales_date_sk": random.choice(self.dimension_keys["date_dim"]),
                "c_salutation": random.choice(["Mr.", "Mrs.", "Ms.", "Dr.", "Prof."]),
                "c_first_name": first_name,
                "c_last_name": last_name,
                "c_preferred_cust_flag": random.choice(["Y", "N"]),
                "c_birth_day": random.randint(1, 28),
                "c_birth_month": random.randint(1, 12),
                "c_birth_year": birth_year,
                "c_birth_country": "UNITED STATES",
                "c_login": f"{first_name[:4].lower()}{random.randint(1, 999)}",  # Shortened to fit 13 char limit
                "c_email_address": f"{first_name.lower()}.{last_name.lower()}@email.com",
                "c_last_review_date": random.choice(self.dimension_keys["date_dim"]),
            }

            customers.append(customer_record)

        self.generated_data["customer"] = customers
        self.dimension_keys["customer"] = [c["c_customer_sk"] for c in customers]
        return customers

    def generate_additional_dimensions(self) -> Dict[str, List[Dict]]:
        """Generate remaining dimension tables."""
        additional_dims = {}

        # Ship Mode
        ship_modes = []
        shipping_methods = [
            ("GROUND", "Standard Ground", ["UPS", "FedEx", "USPS"]),
            ("EXPRESS", "2-Day Express", ["UPS", "FedEx"]),
            ("OVERNIGHT", "Next Day Air", ["UPS", "FedEx"]),
            ("FREIGHT", "Freight Service", ["Yellow", "Conway"]),
            ("MAIL", "Regular Mail", ["USPS"]),
        ]

        for i, (mode_type, description, carriers) in enumerate(shipping_methods):
            ship_mode_sk = i + 1
            carrier = random.choice(carriers)

            ship_modes.append(
                {
                    "sm_ship_mode_sk": ship_mode_sk,
                    "sm_ship_mode_id": f"SHIP{ship_mode_sk:010d}",
                    "sm_type": description,
                    "sm_code": mode_type,
                    "sm_carrier": carrier,
                    "sm_contract": f"Contract-{ship_mode_sk}",
                }
            )

        additional_dims["ship_mode"] = ship_modes
        self.dimension_keys["ship_mode"] = [s["sm_ship_mode_sk"] for s in ship_modes]

        # Time Dimension (business hours)
        time_dims = []
        for hour in range(24):
            for minute in range(0, 60, 15):  # Every 15 minutes
                time_sk = len(time_dims) + 1
                time_value = hour * 3600 + minute * 60  # Seconds since midnight

                shift = "Night" if hour < 6 or hour >= 22 else "Day"
                sub_shift = "Early" if hour < 12 else "Late"
                meal_time = (
                    "Breakfast"
                    if 6 <= hour < 10
                    else (
                        "Lunch"
                        if 11 <= hour < 14
                        else "Dinner" if 17 <= hour < 20 else "Off Hours"
                    )
                )

                time_dims.append(
                    {
                        "t_time_sk": time_sk,
                        "t_time_id": f"TIME{time_sk:010d}",
                        "t_time": time_value,
                        "t_hour": hour,
                        "t_minute": minute,
                        "t_second": 0,
                        "t_am_pm": "AM" if hour < 12 else "PM",
                        "t_shift": shift,
                        "t_sub_shift": sub_shift,
                        "t_meal_time": meal_time,
                    }
                )

        additional_dims["time_dim"] = time_dims
        self.dimension_keys["time_dim"] = [t["t_time_sk"] for t in time_dims]

        # Return Reasons
        reasons = [
            "Defective item",
            "Wrong item shipped",
            "Item not as described",
            "Changed mind",
            "Found better price",
            "Gift return",
            "Size too small",
            "Size too large",
            "Color not as expected",
            "Damaged in shipping",
            "Arrived too late",
            "Duplicate order",
        ]

        reason_dims = []
        for i, desc in enumerate(reasons):
            reason_sk = i + 1
            reason_dims.append(
                {
                    "r_reason_sk": reason_sk,
                    "r_reason_id": f"REASON{reason_sk:010d}",
                    "r_reason_desc": desc,
                }
            )

        additional_dims["reason"] = reason_dims
        self.dimension_keys["reason"] = [r["r_reason_sk"] for r in reason_dims]

        # Income Bands
        income_bands = []
        for i, (band_desc, _) in enumerate(self.income_bands):
            income_sk = i + 1

            # Parse income ranges
            if band_desc == "[0-10K)":
                lower, upper = 0, 10000
            elif band_desc == "[10-20K)":
                lower, upper = 10000, 20000
            elif band_desc == "[20-30K)":
                lower, upper = 20000, 30000
            elif band_desc == "[30-50K)":
                lower, upper = 30000, 50000
            elif band_desc == "[50-75K)":
                lower, upper = 50000, 75000
            elif band_desc == "[75-100K)":
                lower, upper = 75000, 100000
            else:  # '[100K+)'
                lower, upper = 100000, 200000

            income_bands.append(
                {
                    "ib_income_band_sk": income_sk,
                    "ib_lower_bound": lower,
                    "ib_upper_bound": upper,
                }
            )

        additional_dims["income_band"] = income_bands
        self.dimension_keys["income_band"] = [
            ib["ib_income_band_sk"] for ib in income_bands
        ]

        # Household Demographics
        household_demos = []
        for i in range(7200):  # Standard TPC-DS household demographic combinations
            hdemo_sk = i + 1

            # Generate realistic household patterns
            buy_potential_levels = [
                "Unknown",
                "0-500",
                "501-1000",
                "1001-5000",
                "5001-10000",
                "10001+",
            ]
            dep_counts = [0, 1, 2, 3, 4, 5, 6]
            vehicle_counts = [0, 1, 2, 3, 4]

            household_demos.append(
                {
                    "hd_demo_sk": hdemo_sk,
                    "hd_income_band_sk": random.choice(
                        self.dimension_keys["income_band"]
                    ),
                    "hd_buy_potential": random.choice(buy_potential_levels),
                    "hd_dep_count": random.choice(dep_counts),
                    "hd_vehicle_count": random.choice(vehicle_counts),
                }
            )

        additional_dims["household_demographics"] = household_demos
        self.dimension_keys["household_demographics"] = [
            hd["hd_demo_sk"] for hd in household_demos
        ]

        # Web Sites
        web_sites = []
        for i in range(self.config.num_web_sites):
            web_sk = i + 1

            web_sites.append(
                {
                    "web_site_sk": web_sk,
                    "web_site_id": f"SITE{web_sk:010d}",
                    "web_rec_start_date": self.config.start_date,
                    "web_rec_end_date": None,
                    "web_name": f"RetailCorp Online Store {web_sk}",
                    "web_open_date_sk": random.choice(self.dimension_keys["date_dim"]),
                    "web_close_date_sk": None,
                    "web_class": random.choice(["Business", "Consumer", "Both"]),
                    "web_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                    "web_mkt_id": random.randint(1, 10),
                    "web_mkt_class": random.choice(["National", "Regional", "Local"]),
                    "web_mkt_desc": "Online retail market",
                    "web_market_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                    "web_company_id": 1,
                    "web_company_name": "RetailCorp",
                    "web_street_number": str(random.randint(1, 9999)),
                    "web_street_name": self._generate_realistic_name("address"),
                    "web_street_type": random.choice(["St", "Ave", "Blvd"]),
                    "web_suite_number": f"Suite {random.randint(100, 999)}",
                    "web_city": self._generate_realistic_name("city"),
                    "web_county": f'{self._generate_realistic_name("city")} County',
                    "web_state": random.choice(["CA", "NY", "TX", "WA"]),
                    "web_zip": f"{random.randint(10000, 99999)}",
                    "web_country": "United States",
                    "web_gmt_offset": -8.0,
                    "web_tax_percentage": round(random.uniform(0.05, 0.10), 4),
                }
            )

        additional_dims["web_site"] = web_sites
        self.dimension_keys["web_site"] = [ws["web_site_sk"] for ws in web_sites]

        return additional_dims

    def generate_call_centers(self) -> List[Dict]:
        """Generate realistic call centers linked to regions."""
        call_centers = []

        for i, (region_name, states) in enumerate(self.regions.items()):
            cc_sk = i + 1
            state = random.choice(states)

            call_centers.append(
                {
                    "cc_call_center_sk": cc_sk,
                    "cc_call_center_id": f"CC{cc_sk:010d}",
                    "cc_rec_start_date": self.config.start_date,
                    "cc_rec_end_date": None,
                    "cc_closed_date_sk": None,
                    "cc_open_date_sk": random.choice(self.dimension_keys["date_dim"]),
                    "cc_name": f"{region_name} Customer Service Center",
                    "cc_class": "large",
                    "cc_employees": random.randint(50, 200),
                    "cc_sq_ft": random.randint(15000, 50000),
                    "cc_hours": "24x7",
                    "cc_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                    "cc_mkt_id": cc_sk,
                    "cc_mkt_class": "regional",
                    "cc_mkt_desc": f"{region_name} customer service market",
                    "cc_market_manager": f'{self._generate_realistic_name("person_first")} {self._generate_realistic_name("person_last")}',
                    "cc_division": 1,
                    "cc_division_name": "Customer Service Division",
                    "cc_company": 1,
                    "cc_company_name": "RetailCorp",
                    "cc_street_number": str(random.randint(1, 9999)),
                    "cc_street_name": self._generate_realistic_name("address"),
                    "cc_street_type": random.choice(["St", "Ave", "Blvd"]),
                    "cc_suite_number": f"Floor {random.randint(1, 10)}",
                    "cc_city": self._generate_realistic_name("city"),
                    "cc_county": f'{self._generate_realistic_name("city")} County',
                    "cc_state": state,
                    "cc_zip": f"{random.randint(10000, 99999)}",
                    "cc_country": "United States",
                    "cc_gmt_offset": self._get_gmt_offset(state),
                    "cc_tax_percentage": round(random.uniform(0.05, 0.12), 4),
                }
            )

        self.generated_data["call_center"] = call_centers
        self.dimension_keys["call_center"] = [
            cc["cc_call_center_sk"] for cc in call_centers
        ]
        return call_centers

    def generate_promotions(self) -> List[Dict]:
        """Generate realistic promotional campaigns."""
        promotions = []

        # Create seasonal promotions aligned with business patterns
        promo_types = [
            ("Back to School", 8, 9, ["Electronics", "Books", "Clothing"]),
            ("Black Friday", 11, 11, ["Electronics", "Home & Garden"]),
            ("Holiday Shopping", 12, 12, ["Electronics", "Clothing", "Books"]),
            ("Spring Sale", 3, 4, ["Home & Garden", "Clothing"]),
            ("Summer Clearance", 7, 8, ["Sports", "Clothing"]),
            ("End of Year", 12, 12, ["Electronics", "Automotive"]),
        ]

        for year in [2020, 2021, 2022, 2023]:
            for promo_name, start_month, end_month, categories in promo_types:
                promo_sk = len(promotions) + 1

                start_date = date(year, start_month, 1)
                if end_month == start_month:
                    end_date = date(year, end_month, 28)
                else:
                    end_date = date(year, end_month, 15)

                promotions.append(
                    {
                        "p_promo_sk": promo_sk,
                        "p_promo_id": f"PROMO{promo_sk:010d}",
                        "p_start_date_sk": self._date_to_sk(start_date),
                        "p_end_date_sk": self._date_to_sk(end_date),
                        "p_item_sk": None,  # Applies to categories, not specific items
                        "p_cost": round(random.uniform(1000, 50000), 2),
                        "p_response_target": random.randint(5, 25),  # % response rate
                        "p_promo_name": f"{year} {promo_name}",
                        "p_channel_dmail": random.choice(["Y", "N"]),
                        "p_channel_email": "Y",
                        "p_channel_catalog": random.choice(["Y", "N"]),
                        "p_channel_tv": random.choice(["Y", "N"]),
                        "p_channel_radio": random.choice(["Y", "N"]),
                        "p_channel_press": random.choice(["Y", "N"]),
                        "p_channel_event": random.choice(["Y", "N"]),
                        "p_channel_demo": random.choice(["Y", "N"]),
                        "p_channel_details": f'{promo_name} campaign for {", ".join(categories)}',
                        "p_purpose": random.choice(["attract", "retain", "upgrade"]),
                        "p_discount_active": "Y",
                    }
                )

        self.generated_data["promotion"] = promotions
        self.dimension_keys["promotion"] = [p["p_promo_sk"] for p in promotions]
        return promotions

    def _date_to_sk(self, target_date: date) -> int:
        """Convert date to date_sk from our date dimension."""
        if "date_dim" not in self.generated_data:
            return 1

        for date_record in self.generated_data["date_dim"]:
            if date_record["d_date"] == target_date:
                return date_record["d_date_sk"]

        # If exact date not found, return closest
        return random.choice(self.dimension_keys["date_dim"])

    def generate_inventory(self) -> List[Dict]:
        """Generate realistic inventory levels for stores."""
        inventory = []
        seen_combinations = set()  # Track unique combinations to avoid duplicates

        if "store" not in self.generated_data:
            self.generate_stores()
        if "item" not in self.generated_data:
            self.generate_items()
        if "warehouse" not in self.generated_data:
            self.generate_warehouses()
        if "date_dim" not in self.generated_data:
            self.generate_date_dimension()

        # Generate inventory for each warehouse/item/date combination (sample for performance)
        sample_dates = random.sample(
            self.dimension_keys["date_dim"],
            min(10, len(self.dimension_keys["date_dim"])),
        )
        sample_items = random.sample(
            self.dimension_keys["item"], min(500, len(self.dimension_keys["item"]))
        )

        for date_sk in sample_dates:
            for warehouse_sk in self.dimension_keys["warehouse"]:
                for item_sk in sample_items:
                    # Ensure unique combination
                    combination = (date_sk, item_sk, warehouse_sk)
                    if combination in seen_combinations:
                        continue

                    seen_combinations.add(combination)

                    # Realistic inventory levels based on item category
                    item_record = next(
                        i
                        for i in self.generated_data["item"]
                        if i["i_item_sk"] == item_sk
                    )
                    base_qty = {
                        "Electronics": 25,
                        "Clothing": 100,
                        "Books": 50,
                        "Sports": 30,
                        "Automotive": 15,
                        "Home & Garden": 40,
                    }.get(item_record["i_category"], 25)

                    inventory.append(
                        {
                            "inv_date_sk": date_sk,
                            "inv_item_sk": item_sk,
                            "inv_warehouse_sk": warehouse_sk,
                            "inv_quantity_on_hand": random.randint(0, base_qty * 2),
                        }
                    )

                    # Limit inventory records for performance
                    if len(inventory) >= 25000:
                        break

                if len(inventory) >= 25000:
                    break

            if len(inventory) >= 25000:
                break

        self.generated_data["inventory"] = inventory
        return inventory

    def generate_web_pages(self) -> List[Dict]:
        """Generate realistic web pages for online catalog."""
        web_pages = []

        # Create pages for each product category
        for category in self.product_categories.keys():
            for subcategory in self.product_categories[category]:
                page_sk = len(web_pages) + 1

                web_pages.append(
                    {
                        "wp_web_page_sk": page_sk,
                        "wp_web_page_id": f"PAGE{page_sk:010d}",
                        "wp_rec_start_date": self.config.start_date,
                        "wp_rec_end_date": None,
                        "wp_creation_date_sk": random.choice(
                            self.dimension_keys["date_dim"]
                        ),
                        "wp_access_date_sk": random.choice(
                            self.dimension_keys["date_dim"]
                        ),
                        "wp_autogen_flag": random.choice(["Y", "N"]),
                        "wp_customer_sk": None,
                        "wp_url": f"http://www.retailcorp.com/{category.lower()}/{subcategory.lower()}.html",
                        "wp_type": "category",
                        "wp_char_count": random.randint(1000, 5000),
                        "wp_link_count": random.randint(5, 25),
                        "wp_image_count": random.randint(3, 15),
                        "wp_max_ad_count": random.randint(1, 5),
                    }
                )

        self.generated_data["web_page"] = web_pages
        self.dimension_keys["web_page"] = [wp["wp_web_page_sk"] for wp in web_pages]
        return web_pages

    def generate_catalog_pages(self) -> List[Dict]:
        """Generate realistic catalog pages."""
        catalog_pages = []

        for category in self.product_categories.keys():
            for i in range(2):  # 2 pages per category (seasonal catalogs)
                page_sk = len(catalog_pages) + 1

                catalog_pages.append(
                    {
                        "cp_catalog_page_sk": page_sk,
                        "cp_catalog_page_id": f"CATPG{page_sk:010d}",
                        "cp_start_date_sk": random.choice(
                            self.dimension_keys["date_dim"]
                        ),
                        "cp_end_date_sk": random.choice(
                            self.dimension_keys["date_dim"]
                        ),
                        "cp_department": category,
                        "cp_catalog_number": random.randint(1, 100),
                        "cp_catalog_page_number": random.randint(1, 200),
                        "cp_description": f"{category} catalog page",
                        "cp_type": "seasonal",
                    }
                )

        self.generated_data["catalog_page"] = catalog_pages
        self.dimension_keys["catalog_page"] = [
            cp["cp_catalog_page_sk"] for cp in catalog_pages
        ]
        return catalog_pages

    def generate_web_sales(self) -> List[Dict]:
        """Generate realistic web sales transactions."""
        web_sales = []

        # Ensure we have required dimensions
        if "web_site" not in self.generated_data:
            additional_dims = self.generate_additional_dimensions()
        if "web_page" not in self.generated_data:
            self.generate_web_pages()

        # Generate web sales (typically 20-30% of total retail sales)
        num_transactions = min(
            2000, len(self.dimension_keys["customer"]) // 5
        )  # Smaller for faster loading

        for i in range(num_transactions):
            ws_sk = i + 1

            # Select related entities
            customer_sk = random.choice(self.dimension_keys["customer"])
            item_sk = random.choice(self.dimension_keys["item"])
            date_sk = random.choice(self.dimension_keys["date_dim"])
            time_sk = random.choice(self.dimension_keys["time_dim"])
            web_site_sk = random.choice(self.dimension_keys["web_site"])
            web_page_sk = random.choice(self.dimension_keys["web_page"])

            # Get item details for pricing
            item_record = next(
                i for i in self.generated_data["item"] if i["i_item_sk"] == item_sk
            )
            list_price = item_record["i_current_price"]
            wholesale_cost = item_record["i_wholesale_cost"]

            # Web sales typically have different patterns than store sales
            quantity = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
            discount_pct = random.uniform(0, 0.15)  # Lower discounts online
            sales_price = round(list_price * (1 - discount_pct), 2)

            # Calculate amounts
            ext_sales_price = round(sales_price * quantity, 2)
            ext_wholesale_cost = round(wholesale_cost * quantity, 2)
            ext_list_price = round(list_price * quantity, 2)
            ext_tax = round(ext_sales_price * 0.08, 2)  # Avg web tax
            shipping_cost = round(random.uniform(5, 25), 2)
            net_paid = ext_sales_price + shipping_cost
            net_paid_inc_tax = net_paid + ext_tax
            net_profit = net_paid - ext_wholesale_cost - shipping_cost

            web_sales.append(
                {
                    "ws_sold_date_sk": date_sk,
                    "ws_sold_time_sk": time_sk,
                    "ws_ship_date_sk": date_sk
                    + random.randint(1, 7),  # Ships 1-7 days later
                    "ws_item_sk": item_sk,
                    "ws_bill_customer_sk": customer_sk,
                    "ws_bill_cdemo_sk": random.choice(
                        self.dimension_keys["customer_demographics"]
                    ),
                    "ws_bill_hdemo_sk": random.choice(
                        self.dimension_keys["household_demographics"]
                    ),
                    "ws_bill_addr_sk": random.choice(
                        self.dimension_keys["customer_address"]
                    ),
                    "ws_ship_customer_sk": customer_sk,  # Same as bill for simplicity
                    "ws_ship_cdemo_sk": random.choice(
                        self.dimension_keys["customer_demographics"]
                    ),
                    "ws_ship_hdemo_sk": random.choice(
                        self.dimension_keys["household_demographics"]
                    ),
                    "ws_ship_addr_sk": random.choice(
                        self.dimension_keys["customer_address"]
                    ),
                    "ws_web_page_sk": web_page_sk,
                    "ws_web_site_sk": web_site_sk,
                    "ws_ship_mode_sk": random.choice(self.dimension_keys["ship_mode"]),
                    "ws_warehouse_sk": random.choice(self.dimension_keys["warehouse"]),
                    "ws_promo_sk": (
                        random.choice(self.dimension_keys["promotion"])
                        if random.random() < 0.2
                        else None
                    ),
                    "ws_order_number": ws_sk,
                    "ws_quantity": quantity,
                    "ws_wholesale_cost": wholesale_cost,
                    "ws_list_price": list_price,
                    "ws_sales_price": sales_price,
                    "ws_ext_discount_amt": round(
                        (list_price - sales_price) * quantity, 2
                    ),
                    "ws_ext_sales_price": ext_sales_price,
                    "ws_ext_wholesale_cost": ext_wholesale_cost,
                    "ws_ext_list_price": ext_list_price,
                    "ws_ext_tax": ext_tax,
                    "ws_coupon_amt": 0,  # Web doesn't use physical coupons
                    "ws_ext_ship_cost": shipping_cost,
                    "ws_net_paid": net_paid,
                    "ws_net_paid_inc_tax": net_paid_inc_tax,
                    "ws_net_paid_inc_ship": net_paid,
                    "ws_net_paid_inc_ship_tax": net_paid_inc_tax,
                    "ws_net_profit": net_profit,
                }
            )

        self.generated_data["web_sales"] = web_sales
        return web_sales

    def generate_catalog_sales(self) -> List[Dict]:
        """Generate realistic catalog sales transactions."""
        catalog_sales = []

        if "catalog_page" not in self.generated_data:
            self.generate_catalog_pages()

        # Catalog sales (smaller volume, higher value items)
        num_transactions = min(
            1500, len(self.dimension_keys["customer"]) // 10
        )  # Smaller for faster loading

        for i in range(num_transactions):
            cs_sk = i + 1

            # Select related entities
            customer_sk = random.choice(self.dimension_keys["customer"])
            item_sk = random.choice(self.dimension_keys["item"])
            date_sk = random.choice(self.dimension_keys["date_dim"])
            catalog_page_sk = random.choice(self.dimension_keys["catalog_page"])

            # Get item details
            item_record = next(
                i for i in self.generated_data["item"] if i["i_item_sk"] == item_sk
            )
            list_price = item_record["i_current_price"]
            wholesale_cost = item_record["i_wholesale_cost"]

            # Catalog typically higher quantities, seasonal patterns
            quantity = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
            discount_pct = random.uniform(0, 0.20)  # Catalog discounts
            sales_price = round(list_price * (1 - discount_pct), 2)

            # Calculate amounts
            ext_sales_price = round(sales_price * quantity, 2)
            ext_wholesale_cost = round(wholesale_cost * quantity, 2)
            ext_list_price = round(list_price * quantity, 2)
            ext_tax = round(ext_sales_price * 0.07, 2)  # Avg catalog tax
            shipping_cost = round(random.uniform(8, 35), 2)
            net_paid = ext_sales_price + shipping_cost
            net_paid_inc_tax = net_paid + ext_tax
            net_profit = net_paid - ext_wholesale_cost - shipping_cost

            catalog_sales.append(
                {
                    "cs_sold_date_sk": date_sk,
                    "cs_sold_time_sk": None,  # Catalog orders don't have specific time
                    "cs_ship_date_sk": date_sk
                    + random.randint(3, 14),  # Ships 3-14 days later
                    "cs_bill_customer_sk": customer_sk,
                    "cs_bill_cdemo_sk": random.choice(
                        self.dimension_keys["customer_demographics"]
                    ),
                    "cs_bill_hdemo_sk": random.choice(
                        self.dimension_keys["household_demographics"]
                    ),
                    "cs_bill_addr_sk": random.choice(
                        self.dimension_keys["customer_address"]
                    ),
                    "cs_ship_customer_sk": customer_sk,
                    "cs_ship_cdemo_sk": random.choice(
                        self.dimension_keys["customer_demographics"]
                    ),
                    "cs_ship_hdemo_sk": random.choice(
                        self.dimension_keys["household_demographics"]
                    ),
                    "cs_ship_addr_sk": random.choice(
                        self.dimension_keys["customer_address"]
                    ),
                    "cs_call_center_sk": random.choice(
                        self.dimension_keys["call_center"]
                    ),
                    "cs_catalog_page_sk": catalog_page_sk,
                    "cs_ship_mode_sk": random.choice(self.dimension_keys["ship_mode"]),
                    "cs_warehouse_sk": random.choice(self.dimension_keys["warehouse"]),
                    "cs_item_sk": item_sk,
                    "cs_promo_sk": (
                        random.choice(self.dimension_keys["promotion"])
                        if random.random() < 0.25
                        else None
                    ),
                    "cs_order_number": cs_sk,
                    "cs_quantity": quantity,
                    "cs_wholesale_cost": wholesale_cost,
                    "cs_list_price": list_price,
                    "cs_sales_price": sales_price,
                    "cs_ext_discount_amt": round(
                        (list_price - sales_price) * quantity, 2
                    ),
                    "cs_ext_sales_price": ext_sales_price,
                    "cs_ext_wholesale_cost": ext_wholesale_cost,
                    "cs_ext_list_price": ext_list_price,
                    "cs_ext_tax": ext_tax,
                    "cs_coupon_amt": (
                        round(random.uniform(0, 10), 2) if random.random() < 0.15 else 0
                    ),
                    "cs_ext_ship_cost": shipping_cost,
                    "cs_net_paid": net_paid,
                    "cs_net_paid_inc_tax": net_paid_inc_tax,
                    "cs_net_paid_inc_ship": net_paid,
                    "cs_net_paid_inc_ship_tax": net_paid_inc_tax,
                    "cs_net_profit": net_profit,
                }
            )

        self.generated_data["catalog_sales"] = catalog_sales
        return catalog_sales

    def generate_store_returns(self) -> List[Dict]:
        """Generate realistic store returns based on store sales."""
        store_returns = []

        if "store_sales" not in self.generated_data:
            self.generate_store_sales()

        # Typical return rate is 8-15% for retail
        return_rate = 0.12
        num_returns = int(len(self.generated_data["store_sales"]) * return_rate)

        # Sample sales to create returns from
        sales_to_return = random.sample(
            self.generated_data["store_sales"],
            min(num_returns, len(self.generated_data["store_sales"])),
        )

        for i, sale in enumerate(sales_to_return):
            sr_sk = i + 1

            # Return typically happens 1-30 days after sale
            return_date_sk = sale["ss_sold_date_sk"] + random.randint(1, 30)
            reason_sk = random.choice(self.dimension_keys["reason"])

            # Usually return partial quantity
            return_qty = random.randint(1, sale["ss_quantity"])
            ratio = return_qty / sale["ss_quantity"]

            store_returns.append(
                {
                    "sr_returned_date_sk": return_date_sk,
                    "sr_return_time_sk": random.choice(self.dimension_keys["time_dim"]),
                    "sr_item_sk": sale["ss_item_sk"],
                    "sr_customer_sk": sale["ss_customer_sk"],
                    "sr_cdemo_sk": sale["ss_cdemo_sk"],
                    "sr_hdemo_sk": sale["ss_hdemo_sk"],
                    "sr_addr_sk": sale["ss_addr_sk"],
                    "sr_store_sk": sale["ss_store_sk"],
                    "sr_reason_sk": reason_sk,
                    "sr_ticket_number": sale["ss_ticket_number"],
                    "sr_return_quantity": return_qty,
                    "sr_return_amt": round(sale["ss_ext_sales_price"] * ratio, 2),
                    "sr_return_tax": round(sale["ss_ext_tax"] * ratio, 2),
                    "sr_return_amt_inc_tax": round(
                        (sale["ss_ext_sales_price"] + sale["ss_ext_tax"]) * ratio, 2
                    ),
                    "sr_fee": round(random.uniform(0, 5), 2),
                    "sr_return_ship_cost": 0,  # Store returns don't have shipping
                    "sr_refunded_cash": round(
                        sale["ss_ext_sales_price"] * ratio * 0.8, 2
                    ),  # 80% cash refund
                    "sr_reversed_charge": round(
                        sale["ss_ext_sales_price"] * ratio * 0.2, 2
                    ),  # 20% credit
                    "sr_store_credit": round(
                        sale["ss_ext_sales_price"] * ratio * 0.1, 2
                    ),  # 10% store credit
                    "sr_net_loss": round(sale["ss_net_profit"] * ratio, 2),
                }
            )

        self.generated_data["store_returns"] = store_returns
        return store_returns

    def generate_web_returns(self) -> List[Dict]:
        """Generate realistic web returns based on web sales."""
        web_returns = []

        if "web_sales" not in self.generated_data:
            self.generate_web_sales()

        # Web return rate is typically higher (15-25%)
        return_rate = 0.18
        num_returns = int(len(self.generated_data["web_sales"]) * return_rate)

        sales_to_return = random.sample(
            self.generated_data["web_sales"],
            min(num_returns, len(self.generated_data["web_sales"])),
        )

        for i, sale in enumerate(sales_to_return):
            wr_sk = i + 1

            return_date_sk = sale["ws_sold_date_sk"] + random.randint(
                1, 45
            )  # Longer return window online
            reason_sk = random.choice(self.dimension_keys["reason"])

            return_qty = random.randint(1, sale["ws_quantity"])
            ratio = return_qty / sale["ws_quantity"]

            web_returns.append(
                {
                    "wr_returned_date_sk": return_date_sk,
                    "wr_returned_time_sk": random.choice(
                        self.dimension_keys["time_dim"]
                    ),
                    "wr_item_sk": sale["ws_item_sk"],
                    "wr_refunded_customer_sk": sale["ws_bill_customer_sk"],
                    "wr_refunded_cdemo_sk": sale["ws_bill_cdemo_sk"],
                    "wr_refunded_hdemo_sk": sale["ws_bill_hdemo_sk"],
                    "wr_refunded_addr_sk": sale["ws_bill_addr_sk"],
                    "wr_returning_customer_sk": sale["ws_ship_customer_sk"],
                    "wr_returning_cdemo_sk": sale["ws_ship_cdemo_sk"],
                    "wr_returning_hdemo_sk": sale["ws_ship_hdemo_sk"],
                    "wr_returning_addr_sk": sale["ws_ship_addr_sk"],
                    "wr_web_page_sk": sale["ws_web_page_sk"],
                    "wr_reason_sk": reason_sk,
                    "wr_order_number": sale["ws_order_number"],
                    "wr_return_quantity": return_qty,
                    "wr_return_amt": round(sale["ws_ext_sales_price"] * ratio, 2),
                    "wr_return_tax": round(sale["ws_ext_tax"] * ratio, 2),
                    "wr_return_amt_inc_tax": round(
                        (sale["ws_ext_sales_price"] + sale["ws_ext_tax"]) * ratio, 2
                    ),
                    "wr_fee": round(random.uniform(2, 8), 2),  # Return processing fee
                    "wr_return_ship_cost": round(sale["ws_ext_ship_cost"] * ratio, 2),
                    "wr_refunded_cash": round(
                        sale["ws_ext_sales_price"] * ratio * 0.9, 2
                    ),
                    "wr_reversed_charge": round(
                        sale["ws_ext_sales_price"] * ratio * 0.1, 2
                    ),
                    "wr_account_credit": round(
                        sale["ws_ext_sales_price"] * ratio * 0.05, 2
                    ),
                    "wr_net_loss": round(sale["ws_net_profit"] * ratio, 2),
                }
            )

        self.generated_data["web_returns"] = web_returns
        return web_returns

    def generate_catalog_returns(self) -> List[Dict]:
        """Generate realistic catalog returns based on catalog sales."""
        catalog_returns = []

        if "catalog_sales" not in self.generated_data:
            self.generate_catalog_sales()

        # Catalog return rate is moderate (10-15%)
        return_rate = 0.13
        num_returns = int(len(self.generated_data["catalog_sales"]) * return_rate)

        sales_to_return = random.sample(
            self.generated_data["catalog_sales"],
            min(num_returns, len(self.generated_data["catalog_sales"])),
        )

        for i, sale in enumerate(sales_to_return):
            cr_sk = i + 1

            return_date_sk = sale["cs_sold_date_sk"] + random.randint(
                1, 60
            )  # Longer return window
            reason_sk = random.choice(self.dimension_keys["reason"])

            return_qty = random.randint(1, sale["cs_quantity"])
            ratio = return_qty / sale["cs_quantity"]

            catalog_returns.append(
                {
                    "cr_returned_date_sk": return_date_sk,
                    "cr_returned_time_sk": None,  # Catalog returns processed in batches
                    "cr_item_sk": sale["cs_item_sk"],
                    "cr_refunded_customer_sk": sale["cs_bill_customer_sk"],
                    "cr_refunded_cdemo_sk": sale["cs_bill_cdemo_sk"],
                    "cr_refunded_hdemo_sk": sale["cs_bill_hdemo_sk"],
                    "cr_refunded_addr_sk": sale["cs_bill_addr_sk"],
                    "cr_returning_customer_sk": sale["cs_ship_customer_sk"],
                    "cr_returning_cdemo_sk": sale["cs_ship_cdemo_sk"],
                    "cr_returning_hdemo_sk": sale["cs_ship_hdemo_sk"],
                    "cr_returning_addr_sk": sale["cs_ship_addr_sk"],
                    "cr_call_center_sk": sale["cs_call_center_sk"],
                    "cr_catalog_page_sk": sale["cs_catalog_page_sk"],
                    "cr_ship_mode_sk": sale["cs_ship_mode_sk"],
                    "cr_warehouse_sk": sale["cs_warehouse_sk"],
                    "cr_reason_sk": reason_sk,
                    "cr_order_number": sale["cs_order_number"],
                    "cr_return_quantity": return_qty,
                    "cr_return_amount": round(sale["cs_ext_sales_price"] * ratio, 2),
                    "cr_return_tax": round(sale["cs_ext_tax"] * ratio, 2),
                    "cr_return_amt_inc_tax": round(
                        (sale["cs_ext_sales_price"] + sale["cs_ext_tax"]) * ratio, 2
                    ),
                    "cr_fee": round(random.uniform(3, 10), 2),
                    "cr_return_ship_cost": round(sale["cs_ext_ship_cost"] * ratio, 2),
                    "cr_refunded_cash": round(
                        sale["cs_ext_sales_price"] * ratio * 0.85, 2
                    ),
                    "cr_reversed_charge": round(
                        sale["cs_ext_sales_price"] * ratio * 0.15, 2
                    ),
                    "cr_store_credit": round(
                        sale["cs_ext_sales_price"] * ratio * 0.1, 2
                    ),
                    "cr_net_loss": round(sale["cs_net_profit"] * ratio, 2),
                }
            )

        self.generated_data["catalog_returns"] = catalog_returns
        return catalog_returns

    def generate_store_sales(self) -> List[Dict]:
        """Generate realistic store sales fact data with seasonal patterns."""
        if "date_dim" not in self.generated_data:
            self.generate_date_dimension()
        if "store" not in self.generated_data:
            self.generate_stores()
        if "item" not in self.generated_data:
            self.generate_items()
        if "customer" not in self.generated_data:
            self.generate_customers()

        store_sales = []

        # Sample dates for performance (every 7th day to keep realistic patterns)
        sample_dates = [
            d for i, d in enumerate(self.generated_data["date_dim"]) if i % 7 == 0
        ]

        # Generate sales with realistic patterns
        for date_record in sample_dates:
            date_sk = date_record["d_date_sk"]
            current_date = date_record["d_date"]
            month = current_date.month
            is_weekend = date_record["d_weekend"] == "Y"
            is_holiday = date_record["d_holiday"] == "Y"

            # Calculate base sales volume for the day (reduced for performance)
            base_transactions_per_store = 10  # Base transactions per store per day

            # Apply seasonal multiplier
            seasonal_mult = 1.0
            for category in self.seasonal_patterns:
                if random.random() < 0.2:  # 20% chance to apply category seasonality
                    seasonal_mult = self.seasonal_patterns[category][month]
                    break

            # Weekend and holiday boost
            if is_weekend:
                seasonal_mult *= self.config.weekend_boost
            if is_holiday:
                seasonal_mult *= 1.5  # 50% boost on holidays

            transactions_today = int(base_transactions_per_store * seasonal_mult)

            # Generate transactions for each store
            for store_record in self.generated_data["store"]:
                store_sk = store_record["s_store_sk"]

                # Vary transactions per store based on store size
                store_multiplier = (
                    store_record["s_floor_space"] / 50000
                )  # Normalize to average size
                store_transactions = max(1, int(transactions_today * store_multiplier))

                for _ in range(store_transactions):
                    # Select random customer, item, time
                    customer_sk = random.choice(self.dimension_keys["customer"])
                    item_sk = random.choice(self.dimension_keys["item"])
                    time_sk = random.choice(self.dimension_keys["time_dim"])

                    # Get item price
                    item_record = next(
                        i
                        for i in self.generated_data["item"]
                        if i["i_item_sk"] == item_sk
                    )
                    list_price = item_record["i_current_price"]
                    wholesale_cost = item_record["i_wholesale_cost"]

                    # Generate realistic quantities and pricing
                    quantity = random.choices(
                        [1, 2, 3, 4, 5], weights=[60, 25, 10, 3, 2]
                    )[0]

                    # Apply random discount (0-30%)
                    discount_pct = (
                        random.uniform(0, 0.3) if random.random() < 0.4 else 0
                    )
                    sales_price = round(list_price * (1 - discount_pct), 2)

                    # Calculate totals
                    ext_sales_price = round(sales_price * quantity, 2)
                    ext_wholesale_cost = round(wholesale_cost * quantity, 2)
                    ext_list_price = round(list_price * quantity, 2)
                    ext_tax = round(
                        ext_sales_price * store_record["s_tax_precentage"], 2
                    )
                    coupon_amt = (
                        round(random.uniform(0, 5), 2) if random.random() < 0.1 else 0
                    )
                    net_paid = ext_sales_price - coupon_amt
                    net_paid_inc_tax = net_paid + ext_tax
                    net_profit = net_paid - ext_wholesale_cost

                    sale_record = {
                        "ss_sold_date_sk": date_sk,
                        "ss_sold_time_sk": time_sk,
                        "ss_item_sk": item_sk,
                        "ss_customer_sk": customer_sk,
                        "ss_cdemo_sk": random.choice(
                            self.dimension_keys["customer_demographics"]
                        ),
                        "ss_hdemo_sk": random.choice(
                            self.dimension_keys["household_demographics"]
                        ),
                        "ss_addr_sk": random.choice(
                            self.dimension_keys["customer_address"]
                        ),
                        "ss_store_sk": store_sk,
                        "ss_promo_sk": (
                            random.randint(1, 300) if random.random() < 0.3 else None
                        ),
                        "ss_ticket_number": len(store_sales) + 1,
                        "ss_quantity": quantity,
                        "ss_wholesale_cost": wholesale_cost,
                        "ss_list_price": list_price,
                        "ss_sales_price": sales_price,
                        "ss_ext_discount_amt": round(
                            (list_price - sales_price) * quantity, 2
                        ),
                        "ss_ext_sales_price": ext_sales_price,
                        "ss_ext_wholesale_cost": ext_wholesale_cost,
                        "ss_ext_list_price": ext_list_price,
                        "ss_ext_tax": ext_tax,
                        "ss_coupon_amt": coupon_amt,
                        "ss_net_paid": net_paid,
                        "ss_net_paid_inc_tax": net_paid_inc_tax,
                        "ss_net_profit": net_profit,
                    }

                    store_sales.append(sale_record)

                    # Limit total sales records for performance
                    if (
                        len(store_sales) >= 100000
                    ):  # 100K records max for faster loading
                        break

                if len(store_sales) >= 100000:
                    break

            if len(store_sales) >= 100000:
                break

        self.generated_data["store_sales"] = store_sales
        return store_sales

    def _get_gmt_offset(self, state: str) -> float:
        """Get realistic GMT offset based on state."""
        timezone_map = {
            # Pacific: -8
            "CA": -8.0,
            "WA": -8.0,
            "OR": -8.0,
            "NV": -8.0,
            # Mountain: -7
            "AZ": -7.0,
            "UT": -7.0,
            "CO": -7.0,
            "ID": -7.0,
            "MT": -7.0,
            "WY": -7.0,
            # Central: -6
            "TX": -6.0,
            "OK": -6.0,
            "AR": -6.0,
            "LA": -6.0,
            "MS": -6.0,
            "AL": -6.0,
            "TN": -6.0,
            "IL": -6.0,
            "WI": -6.0,
            "MN": -6.0,
            "IA": -6.0,
            "MO": -6.0,
            "ND": -6.0,
            "SD": -6.0,
            "NE": -6.0,
            "KS": -6.0,
            # Eastern: -5
            "FL": -5.0,
            "GA": -5.0,
            "NC": -5.0,
            "SC": -5.0,
            "VA": -5.0,
            "NY": -5.0,
            "NJ": -5.0,
            "PA": -5.0,
            "CT": -5.0,
            "MA": -5.0,
            "ME": -5.0,
            "VT": -5.0,
            "NH": -5.0,
            "RI": -5.0,
            "IN": -5.0,
            "OH": -5.0,
            "MI": -5.0,
        }
        return timezone_map.get(state, -5.0)  # Default to Eastern

    def write_to_files(self, output_dir: str):
        """Write generated data to CSV files compatible with TPC-DS loaders."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        console.print(f"Writing synthetic data files to: {output_path.absolute()}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:

            # Generate and write each table in proper dependency order
            if self.config.scale_factor == 0:  # Test mode - only essential tables
                tables_to_generate = [
                    # Minimal set for testing (maintaining dependencies)
                    ("date_dim", self.generate_date_dimension),
                    ("customer", self.generate_customers),
                    ("item", self.generate_items),
                    ("store", self.generate_stores),
                    ("warehouse", self.generate_warehouses),
                    # Need additional_dimensions for time_dim (required by sales tables)
                    ("additional_dimensions", self.generate_additional_dimensions),
                    ("store_sales", self.generate_store_sales),
                ]
            else:  # Full mode - all tables
                tables_to_generate = [
                    # Core dimension tables first (for referential integrity)
                    ("date_dim", self.generate_date_dimension),
                    ("customer_demographics", self.generate_customer_demographics),
                    ("customer_address", self.generate_customer_addresses),
                    ("warehouse", self.generate_warehouses),
                    ("store", self.generate_stores),
                    ("item", self.generate_items),
                    ("customer", self.generate_customers),
                    # Additional core dimensions
                    ("additional_dimensions", self.generate_additional_dimensions),
                    # Business operational tables
                    ("call_center", self.generate_call_centers),
                    ("promotion", self.generate_promotions),
                    ("inventory", self.generate_inventory),
                    # Web and catalog infrastructure
                    ("web_page", self.generate_web_pages),
                    ("catalog_page", self.generate_catalog_pages),
                    # Major fact tables (sales channels)
                    ("store_sales", self.generate_store_sales),
                    ("web_sales", self.generate_web_sales),
                    ("catalog_sales", self.generate_catalog_sales),
                    # Returns fact tables (based on sales)
                    ("store_returns", self.generate_store_returns),
                    ("web_returns", self.generate_web_returns),
                    ("catalog_returns", self.generate_catalog_returns),
                ]

            task = progress.add_task(
                "Generating synthetic data...", total=len(tables_to_generate)
            )

            for table_name, generator_func in tables_to_generate:
                progress.update(task, description=f"Generating {table_name}...")

                if table_name == "additional_dimensions":
                    # Handle multiple tables returned by this function
                    additional_tables = generator_func()
                    for sub_table_name, sub_data in additional_tables.items():
                        self._write_table_to_file(output_path, sub_table_name, sub_data)
                else:
                    data = generator_func()
                    self._write_table_to_file(output_path, table_name, data)

                progress.advance(task)

            # Count total files generated
            total_files = len(list(output_path.glob("*.dat")))
            console.print(
                f"✅ Generated {total_files} synthetic data files", style="green"
            )

    def _write_table_to_file(
        self, output_path: Path, table_name: str, data: List[Dict]
    ):
        """Write a single table to file."""
        csv_file = output_path / f"{table_name}.dat"
        with open(csv_file, "w") as f:
            for record in data:
                # Convert to pipe-delimited format (TPC-DS standard)
                values = []
                for value in record.values():
                    if value is None:
                        values.append("")
                    elif isinstance(value, date):
                        values.append(value.strftime("%Y-%m-%d"))
                    else:
                        values.append(str(value))
                f.write("|".join(values) + "|\n")


def create_synthetic_data(scale: int = 1, output_dir: str = "./synthetic_data") -> bool:
    """Main entry point for synthetic data generation.

    Args:
        scale: Scale factor for data generation:
               - 0: Test mode (tiny dataset for testing)
               - 1: Small dataset (default)
               - 2+: Larger datasets
        output_dir: Directory to write data files
    """

    if not HAS_FAKER:
        console.print(
            "⚠️  Faker library not found. Installing for better synthetic data...",
            style="yellow",
        )
        try:
            import subprocess

            subprocess.run(["pip", "install", "faker"], check=True, capture_output=True)
            console.print("✅ Faker installed successfully", style="green")
            # Re-import after installation
            globals()["Faker"] = __import__("faker").Faker
            globals()["HAS_FAKER"] = True
        except Exception as e:
            console.print(
                f"⚠️  Could not install Faker: {e}. Using basic synthetic data.",
                style="yellow",
            )

    try:
        # Handle test mode (scale 0) for fast testing
        if scale == 0:
            console.print(
                "🧪 Test mode: Generating minimal dataset for testing", style="yellow"
            )
            from datetime import date

            config = DataGenerationConfig(
                scale_factor=0,
                start_date=date(2023, 1, 1),  # Short date range for testing
                end_date=date(2023, 1, 7),  # Just 1 week of dates
                num_customers=5,  # Minimal customers
                num_items=3,  # Minimal items
                num_stores=1,  # Single store
                num_warehouses=1,  # Single warehouse
                num_web_sites=1,  # Single web site
                num_call_centers=1,  # Single call center
            )
        else:
            # Scale the configuration based on scale factor for normal operation
            config = DataGenerationConfig(
                scale_factor=scale,
                num_customers=min(100000 * scale, 1000000),  # Cap at 1M customers
                num_items=18000 * scale,
                num_stores=max(12, int(12 * (scale**0.5))),  # Scale stores more slowly
                num_warehouses=max(5, int(5 * (scale**0.5))),
            )

        generator = SyntheticDataGenerator(config)
        generator.write_to_files(output_dir)

        console.print(
            f"🎉 Synthetic TPC-DS data generated successfully!", style="bold green"
        )
        console.print(
            f"📁 Files written to: {Path(output_dir).absolute()}", style="cyan"
        )
        console.print(
            "📋 This data is synthetic and license-free for enterprise use",
            style="green",
        )

        return True

    except Exception as e:
        console.print(f"❌ Error generating synthetic data: {e}", style="red")
        return False


if __name__ == "__main__":
    create_synthetic_data()
