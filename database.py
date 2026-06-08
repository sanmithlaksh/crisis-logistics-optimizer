import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase_client: Client = None

# Fallback mode flag
USING_SQLITE_FALLBACK = False

if SUPABASE_URL and SUPABASE_URL != "https://your-project-id.supabase.co" and SUPABASE_KEY and SUPABASE_KEY != "your-supabase-anon-key-here":
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase successfully!")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}", file=sys.stderr)
        print("Falling back to local SQLite database for development stability.", file=sys.stderr)
        USING_SQLITE_FALLBACK = True
else:
    print("WARNING: Supabase credentials not configured or using placeholders in .env.", file=sys.stderr)
    print("Falling back to local SQLite database for development stability.", file=sys.stderr)
    print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file to use Supabase.", file=sys.stderr)
    USING_SQLITE_FALLBACK = True

# --- SQLite Fallback Implementation ---
# To ensure the application remains robust and usable even before the user sets up their Supabase project
import sqlite3
SQLITE_DB_PATH = 'crisis_logistics.db'

def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API Methods ---

def get_zones():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM zones")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    else:
        response = supabase_client.table('zones').select('*').execute()
        return response.data

def get_resources():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    else:
        response = supabase_client.table('resources').select('*').execute()
        return response.data

def get_requests():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        # Join zones table to get coordinates and names
        cursor.execute("""
            SELECT r.*, z.name as zone_name, z.severity, z.population, z.latitude, z.longitude 
            FROM requests r 
            JOIN zones z ON r.zone_id = z.id
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    else:
        response = supabase_client.table('requests').select('*, zones(*)').execute()
        # Flatten structure to match expected format
        flattened = []
        for req in response.data:
            zone = req.get('zones', {})
            flattened.append({
                'request_id': req['request_id'],
                'zone_id': req['zone_id'],
                'resource_type': req['resource_type'],
                'quantity': req['quantity'],
                'priority': req['priority'],
                'status': req['status'],
                'timestamp': req['timestamp'],
                'zone_name': zone.get('name') if zone else 'Unknown',
                'severity': zone.get('severity') if zone else 'Medium',
                'population': zone.get('population') if zone else 0,
                'latitude': zone.get('latitude') if zone else 0.0,
                'longitude': zone.get('longitude') if zone else 0.0
            })
        return flattened

def get_vehicles():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    else:
        response = supabase_client.table('vehicles').select('*').execute()
        return response.data

def get_roads():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM roads")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    else:
        response = supabase_client.table('roads').select('*').execute()
        return response.data

def insert_request(zone_id, resource_type, quantity, priority, status='Pending'):
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO requests (zone_id, resource_type, quantity, priority, status)
            VALUES (?, ?, ?, ?, ?)
        """, (zone_id, resource_type, quantity, priority, status))
        conn.commit()
        conn.close()
    else:
        supabase_client.table('requests').insert({
            'zone_id': zone_id,
            'resource_type': resource_type,
            'quantity': quantity,
            'priority': priority,
            'status': status
        }).execute()

def update_request_status(request_id, status):
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE requests SET status = ? WHERE request_id = ?", (status, request_id))
        conn.commit()
        conn.close()
    else:
        supabase_client.table('requests').update({'status': status}).eq('request_id', request_id).execute()

def update_resource_quantity(resource_name, quantity):
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE resources SET available_quantity = ? WHERE resource_name = ?", (quantity, resource_name))
        conn.commit()
        conn.close()
    else:
        supabase_client.table('resources').update({'available_quantity': quantity}).eq('resource_name', resource_name).execute()

def update_vehicle_status(vehicle_id, status):
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET status = ? WHERE vehicle_id = ?", (status, vehicle_id))
        conn.commit()
        conn.close()
    else:
        supabase_client.table('vehicles').update({'status': status}).eq('vehicle_id', vehicle_id).execute()

def reset_database_state(zones_list, resources_list, vehicles_list, roads_list):
    """
    Clears all tables and populates them with new baseline data.
    """
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requests")
        cursor.execute("DELETE FROM roads")
        cursor.execute("DELETE FROM vehicles")
        cursor.execute("DELETE FROM resources")
        cursor.execute("DELETE FROM zones")
        
        # Insert zones
        cursor.executemany("""
            INSERT INTO zones (id, name, latitude, longitude, population, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, zones_list)
        
        # Insert resources
        cursor.executemany("""
            INSERT INTO resources (resource_id, resource_name, available_quantity, unit_weight, utility_value)
            VALUES (?, ?, ?, ?, ?)
        """, resources_list)
        
        # Insert vehicles
        cursor.executemany("""
            INSERT INTO vehicles (vehicle_id, name, type, capacity_weight, speed_kmh, cost_per_km, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, vehicles_list)
        
        # Insert roads
        cursor.executemany("""
            INSERT INTO roads (road_id, source, destination, distance_km, risk_level)
            VALUES (?, ?, ?, ?, ?)
        """, roads_list)
        
        conn.commit()
        conn.close()
    else:
        # Clear tables
        supabase_client.table('requests').delete().neq('request_id', 0).execute()
        supabase_client.table('roads').delete().neq('road_id', 0).execute()
        supabase_client.table('vehicles').delete().neq('vehicle_id', 0).execute()
        supabase_client.table('resources').delete().neq('resource_id', 0).execute()
        supabase_client.table('zones').delete().neq('id', 0).execute()
        
        # Format zones for Supabase
        zones_data = [{'id': z[0], 'name': z[1], 'latitude': z[2], 'longitude': z[3], 'population': z[4], 'severity': z[5]} for z in zones_list]
        supabase_client.table('zones').insert(zones_data).execute()
        
        # Format resources for Supabase
        resources_data = [{'resource_id': r[0], 'resource_name': r[1], 'available_quantity': r[2], 'unit_weight': r[3], 'utility_value': r[4]} for r in resources_list]
        supabase_client.table('resources').insert(resources_data).execute()
        
        # Format vehicles for Supabase
        vehicles_data = [{'vehicle_id': v[0], 'name': v[1], 'type': v[2], 'capacity_weight': v[3], 'speed_kmh': v[4], 'cost_per_km': v[5], 'status': v[6]} for v in vehicles_list]
        supabase_client.table('vehicles').insert(vehicles_data).execute()
        
        # Format roads for Supabase
        roads_data = [{'road_id': rd[0], 'source': rd[1], 'destination': rd[2], 'distance_km': rd[3], 'risk_level': rd[4]} for rd in roads_list]
        supabase_client.table('roads').insert(roads_data).execute()

def seed_default_if_empty():
    """Seeds the database with default values if it is empty."""
    zones = get_zones()
    if len(zones) == 0:
        print("Database is empty. Seeding default data...")
        zones_list = [
            (1, 'Zone A (Glendale)', 34.1425, -118.2437, 12000, 'Critical'),
            (2, 'Zone B (Pasadena)', 34.1478, -118.1445, 18000, 'High'),
            (3, 'Zone C (East LA)', 34.0224, -118.1670, 25000, 'Medium'),
            (4, 'Zone D (Torrance)', 33.8358, -118.3406, 15000, 'Critical'),
            (5, 'Zone E (Santa Monica)', 34.0194, -118.4912, 10000, 'Low'),
            (6, 'Zone F (Hollywood)', 34.0928, -118.3287, 22000, 'High'),
            (7, 'Zone G (Long Beach)', 33.7701, -118.1937, 30000, 'Critical'),
            (8, 'Zone H (Malibu)', 34.0259, -118.7798, 8000, 'Low'),
            (9, 'Zone I (Burbank)', 34.1808, -118.3090, 14000, 'Medium'),
            (10, 'Zone J (Anaheim)', 33.8366, -117.9143, 35000, 'High'),
            (11, 'Zone K (Beverly Hills)', 34.0736, -118.4004, 9000, 'Medium'),
            (12, 'Zone L (Inglewood)', 33.9617, -118.3531, 16000, 'High'),
            (13, 'Zone M (Downey)', 33.9401, -118.1332, 14000, 'Medium'),
            (14, 'Zone N (El Monte)', 34.0686, -118.0276, 20000, 'High'),
            (15, 'Zone O (Compton)', 33.8958, -118.2201, 18000, 'Critical'),
            (16, 'Zone P (Pomona)', 34.0551, -117.7500, 25000, 'Medium'),
            (17, 'Zone Q (Redondo Beach)', 33.8492, -118.3884, 11000, 'Low'),
            (18, 'Zone R (Manhattan Beach)', 33.8847, -118.4109, 9000, 'Low'),
            (19, 'Zone S (Culver City)', 34.0211, -118.3965, 12000, 'Medium'),
            (20, 'Zone T (Carson)', 33.8317, -118.2817, 15000, 'High'),
            (21, 'Zone U (Gardena)', 33.8883, -118.3090, 13000, 'Medium'),
            (22, 'Zone V (West Covina)', 34.0686, -117.9390, 22000, 'High'),
            (23, 'Zone W (Norwalk)', 33.9081, -118.0817, 17000, 'Critical')
        ]
        resources_list = [
            (1, 'Medicine', 500, 2.0, 100),
            (2, 'Food Packets', 1000, 1.0, 40),
            (3, 'Water Crate', 800, 5.0, 50),
            (4, 'Fuel Ltrs', 400, 3.0, 70),
            (5, 'Rescue Gear', 100, 15.0, 90),
            (6, 'Emergency Personnel', 50, 0.0, 120)
        ]
        vehicles_list = [
            (1, 'Truck Alpha', 'Heavy Truck', 400.0, 60.0, 5.0, 'Available'),
            (2, 'Truck Beta', 'Medium Truck', 250.0, 70.0, 3.5, 'Available'),
            (3, '4x4 Rescue Unit', 'Offroad Vehicle', 150.0, 80.0, 2.5, 'Available'),
            (4, 'Rescue Heli-1', 'Helicopter', 300.0, 180.0, 15.0, 'Available'),
            (5, 'Aid Drone X', 'Drone', 40.0, 50.0, 1.0, 'Available')
        ]
        roads_list = [
            (1, 'Depot', 'Zone A (Glendale)', 10.5, 'Normal'),
            (2, 'Depot', 'Zone C (East LA)', 8.2, 'Normal'),
            (3, 'Depot', 'Zone S (Culver City)', 15.0, 'Normal'),
            (4, 'Zone A (Glendale)', 'Zone B (Pasadena)', 9.2, 'Normal'),
            (5, 'Zone B (Pasadena)', 'Zone C (East LA)', 14.5, 'Normal'),
            (6, 'Zone A (Glendale)', 'Zone F (Hollywood)', 11.4, 'Normal'),
            (7, 'Zone F (Hollywood)', 'Zone K (Beverly Hills)', 6.0, 'Normal'),
            (8, 'Zone K (Beverly Hills)', 'Zone E (Santa Monica)', 12.5, 'Normal'),
            (9, 'Zone E (Santa Monica)', 'Zone H (Malibu)', 25.0, 'Normal'),
            (10, 'Zone A (Glendale)', 'Zone I (Burbank)', 6.5, 'Normal'),
            (11, 'Zone C (East LA)', 'Zone D (Torrance)', 27.1, 'Normal'),
            (12, 'Zone D (Torrance)', 'Zone G (Long Beach)', 15.0, 'Normal'),
            (13, 'Zone G (Long Beach)', 'Zone J (Anaheim)', 35.0, 'Normal'),
            (14, 'Zone F (Hollywood)', 'Zone I (Burbank)', 8.5, 'Normal'),
            (15, 'Zone C (East LA)', 'Zone M (Downey)', 12.0, 'Normal'),
            (16, 'Zone M (Downey)', 'Zone W (Norwalk)', 8.0, 'Normal'),
            (17, 'Zone W (Norwalk)', 'Zone J (Anaheim)', 20.0, 'Normal'),
            (18, 'Zone C (East LA)', 'Zone L (Inglewood)', 18.0, 'Normal'),
            (19, 'Zone M (Downey)', 'Zone O (Compton)', 10.0, 'Normal'),
            (20, 'Zone B (Pasadena)', 'Zone N (El Monte)', 12.0, 'Normal'),
            (21, 'Zone N (El Monte)', 'Zone V (West Covina)', 10.0, 'Normal'),
            (22, 'Zone V (West Covina)', 'Zone P (Pomona)', 15.0, 'Normal'),
            (23, 'Zone E (Santa Monica)', 'Zone R (Manhattan Beach)', 18.0, 'Normal'),
            (24, 'Zone R (Manhattan Beach)', 'Zone Q (Redondo Beach)', 5.0, 'Normal'),
            (25, 'Zone Q (Redondo Beach)', 'Zone D (Torrance)', 6.0, 'Normal'),
            (26, 'Zone S (Culver City)', 'Zone U (Gardena)', 15.0, 'Normal'),
            (27, 'Zone U (Gardena)', 'Zone T (Carson)', 8.0, 'Normal'),
            (28, 'Zone T (Carson)', 'Zone G (Long Beach)', 9.0, 'Normal')
        ]
        reset_database_state(zones_list, resources_list, vehicles_list, roads_list)

# Attempt to seed on import
try:
    seed_default_if_empty()
except Exception as e:
    print(f"Error seeding database: {e}", file=sys.stderr)
