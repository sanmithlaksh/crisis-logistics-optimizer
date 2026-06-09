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
import sqlite3
SQLITE_DB_PATH = 'crisis_logistics.db'

def check_and_upgrade_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            population INTEGER NOT NULL,
            severity TEXT,
            is_active INTEGER DEFAULT 1,
            is_depot INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            resource_id INTEGER PRIMARY KEY,
            resource_name TEXT UNIQUE NOT NULL,
            available_quantity INTEGER NOT NULL,
            unit_weight REAL NOT NULL,
            utility_value INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            resource_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            priority REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(zone_id) REFERENCES zones(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            capacity_weight REAL NOT NULL,
            speed_kmh REAL NOT NULL,
            cost_per_km REAL NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roads (
            road_id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            distance_km REAL NOT NULL,
            risk_level TEXT DEFAULT 'Normal'
        )
    """)
    
    # Check for columns is_active and is_depot
    cursor.execute("PRAGMA table_info(zones)")
    cols = [r['name'] for r in cursor.fetchall()]
    if 'is_active' not in cols:
        cursor.execute("ALTER TABLE zones ADD COLUMN is_active INTEGER DEFAULT 1")
    if 'is_depot' not in cols:
        cursor.execute("ALTER TABLE zones ADD COLUMN is_depot INTEGER DEFAULT 0")
    conn.commit()

def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        check_and_upgrade_schema(conn)
    except Exception as e:
        print(f"Error checking and upgrading SQLite schema: {e}", file=sys.stderr)
    return conn

# --- API Methods ---

def get_zones():
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM zones")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        for r in rows:
            if 'is_active' not in r:
                r['is_active'] = 1
            if 'is_depot' not in r:
                r['is_depot'] = 0
        return rows
    else:
        response = supabase_client.table('zones').select('*').execute()
        data = response.data
        for r in data:
            if 'is_active' not in r:
                r['is_active'] = 1
            if 'is_depot' not in r:
                r['is_depot'] = 0
        return data

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
        cursor.execute("""
            SELECT r.*, z.name as zone_name, z.severity, z.population, z.latitude, z.longitude, z.is_active, z.is_depot
            FROM requests r 
            JOIN zones z ON r.zone_id = z.id
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        for r in rows:
            if 'is_active' not in r:
                r['is_active'] = 1
            if 'is_depot' not in r:
                r['is_depot'] = 0
        return rows
    else:
        response = supabase_client.table('requests').select('*, zones(*)').execute()
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
                'longitude': zone.get('longitude') if zone else 0.0,
                'is_active': zone.get('is_active', True) if zone else True,
                'is_depot': zone.get('is_depot', False) if zone else False
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

# --- Active Upgrades database edits ---

def update_zone_active_status(zone_id, is_active):
    """Toggles active/inactive state of a zone."""
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE zones SET is_active = ? WHERE id = ?", (1 if is_active else 0, zone_id))
        conn.commit()
        conn.close()
    else:
        try:
            supabase_client.table('zones').update({'is_active': is_active}).eq('id', zone_id).execute()
        except Exception as e:
            print(f"Failed to update is_active in Supabase: {e}", file=sys.stderr)

def update_road_hazard(source, destination, risk_level):
    """Updates the hazard level of a specific road."""
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE roads 
            SET risk_level = ? 
            WHERE (source = ? AND destination = ?) OR (source = ? AND destination = ?)
        """, (risk_level, source, destination, destination, source))
        conn.commit()
        conn.close()
    else:
        try:
            supabase_client.table('roads').update({'risk_level': risk_level}).eq('source', source).eq('destination', destination).execute()
            supabase_client.table('roads').update({'risk_level': risk_level}).eq('source', destination).eq('destination', source).execute()
        except Exception as e:
            print(f"Failed to update road risk in Supabase: {e}", file=sys.stderr)

def insert_new_zones_bulk(new_zones, new_roads, new_requests):
    """Inserts a batch of dynamically generated zones, roads, and requests."""
    if USING_SQLITE_FALLBACK:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        
        # Insert zones
        cursor.executemany("""
            INSERT OR REPLACE INTO zones (id, name, latitude, longitude, population, severity, is_active, is_depot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, new_zones)
        
        # Insert roads
        cursor.executemany("""
            INSERT INTO roads (source, destination, distance_km, risk_level)
            VALUES (?, ?, ?, ?)
        """, new_roads)
        
        # Insert requests
        cursor.executemany("""
            INSERT INTO requests (zone_id, resource_type, quantity, priority, status)
            VALUES (?, ?, ?, ?, ?)
        """, new_requests)
        
        conn.commit()
        conn.close()
    else:
        try:
            # Format zones for Supabase
            zones_data = [{'id': z[0], 'name': z[1], 'latitude': z[2], 'longitude': z[3], 'population': z[4], 'severity': z[5], 'is_active': bool(z[6]), 'is_depot': bool(z[7])} for z in new_zones]
            supabase_client.table('zones').insert(zones_data).execute()
            
            # Format roads
            roads_data = [{'source': rd[0], 'destination': rd[1], 'distance_km': rd[2], 'risk_level': rd[3]} for rd in new_roads]
            supabase_client.table('roads').insert(roads_data).execute()
            
            # Format requests
            reqs_data = [{'zone_id': req[0], 'resource_type': req[1], 'quantity': req[2], 'priority': req[3], 'status': req[4]} for req in new_requests]
            supabase_client.table('requests').insert(reqs_data).execute()
        except Exception as e:
            print(f"Failed to insert bulk simulation data to Supabase: {e}", file=sys.stderr)

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
            INSERT INTO zones (id, name, latitude, longitude, population, severity, is_active, is_depot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        
        # Format zones for Supabase (with try-except for column check fallback)
        try:
            zones_data = [{'id': z[0], 'name': z[1], 'latitude': z[2], 'longitude': z[3], 'population': z[4], 'severity': z[5], 'is_active': bool(z[6]), 'is_depot': bool(z[7])} for z in zones_list]
            supabase_client.table('zones').insert(zones_data).execute()
        except Exception as e:
            print(f"Supabase zones insert failed (missing is_active/is_depot columns). Using old schema fallback: {e}", file=sys.stderr)
            zones_data_fallback = [{'id': z[0], 'name': z[1], 'latitude': z[2], 'longitude': z[3], 'population': z[4], 'severity': z[5]} for z in zones_list]
            supabase_client.table('zones').insert(zones_data_fallback).execute()
        
        # Format resources
        resources_data = [{'resource_id': r[0], 'resource_name': r[1], 'available_quantity': r[2], 'unit_weight': r[3], 'utility_value': r[4]} for r in resources_list]
        supabase_client.table('resources').insert(resources_data).execute()
        
        # Format vehicles
        vehicles_data = [{'vehicle_id': v[0], 'name': v[1], 'type': v[2], 'capacity_weight': v[3], 'speed_kmh': v[4], 'cost_per_km': v[5], 'status': v[6]} for v in vehicles_list]
        supabase_client.table('vehicles').insert(vehicles_data).execute()
        
        # Format roads
        roads_data = [{'road_id': rd[0], 'source': rd[1], 'destination': rd[2], 'distance_km': rd[3], 'risk_level': rd[4]} for rd in roads_list]
        supabase_client.table('roads').insert(roads_data).execute()

def seed_default_if_empty():
    """Seeds the database with default values if it is empty."""
    zones = get_zones()
    if len(zones) == 0:
        print("Database is empty. Seeding default data...")
        zones_list = [
            (1, 'Zone A (Glendale)', 34.1425, -118.2437, 12000, 'Critical', 1, 0),
            (2, 'Zone B (Pasadena)', 34.1478, -118.1445, 18000, 'High', 1, 0),
            (3, 'Zone C (East LA)', 34.0224, -118.1670, 25000, 'Medium', 1, 0),
            (4, 'Zone D (Torrance)', 33.8358, -118.3406, 15000, 'Critical', 1, 0),
            (5, 'Zone E (Santa Monica)', 34.0194, -118.4912, 10000, 'Low', 1, 0),
            (6, 'Zone F (Hollywood)', 34.0928, -118.3287, 22000, 'High', 1, 0),
            (7, 'Zone G (Long Beach)', 33.7701, -118.1937, 30000, 'Critical', 1, 0),
            (8, 'Zone H (Malibu)', 34.0259, -118.7798, 8000, 'Low', 1, 0),
            (9, 'Zone I (Burbank)', 34.1808, -118.3090, 14000, 'Medium', 1, 0),
            (10, 'Zone J (Anaheim)', 33.8366, -117.9143, 35000, 'High', 1, 0),
            (11, 'Zone K (Beverly Hills)', 34.0736, -118.4004, 9000, 'Medium', 1, 0),
            (12, 'Zone L (Inglewood)', 33.9617, -118.3531, 16000, 'High', 1, 0),
            (13, 'Zone M (Downey)', 33.9401, -118.1332, 14000, 'Medium', 1, 0),
            (14, 'Zone N (El Monte)', 34.0686, -118.0276, 20000, 'High', 1, 0),
            (15, 'Zone O (Compton)', 33.8958, -118.2201, 18000, 'Critical', 1, 0),
            (16, 'Zone P (Pomona)', 34.0551, -117.7500, 25000, 'Medium', 1, 0),
            (17, 'Zone Q (Redondo Beach)', 33.8492, -118.3884, 11000, 'Low', 1, 0),
            (18, 'Zone R (Manhattan Beach)', 33.8847, -118.4109, 9000, 'Low', 1, 0),
            (19, 'Zone S (Culver City)', 34.0211, -118.3965, 12000, 'Medium', 1, 0),
            (20, 'Zone T (Carson)', 33.8317, -118.2817, 15000, 'High', 1, 0),
            (21, 'Zone U (Gardena)', 33.8883, -118.3090, 13000, 'Medium', 1, 0),
            (22, 'Zone V (West Covina)', 34.0686, -117.9390, 22000, 'High', 1, 0),
            (23, 'Zone W (Norwalk)', 33.9081, -118.0817, 17000, 'Critical', 1, 0),
            (24, 'Depot A (Central)', 34.0522, -118.2437, 0, 'Low', 1, 1),
            (25, 'Depot B (South)', 33.8358, -118.2817, 0, 'Low', 1, 1),
            (26, 'Depot C (West)', 34.0211, -118.3965, 0, 'Low', 1, 1)
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
            (1, 'Depot A (Central)', 'Zone A (Glendale)', 10.5, 'Normal'),
            (2, 'Depot A (Central)', 'Zone C (East LA)', 8.2, 'Normal'),
            (3, 'Depot A (Central)', 'Zone S (Culver City)', 15.0, 'Normal'),
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
            (28, 'Zone T (Carson)', 'Zone G (Long Beach)', 9.0, 'Normal'),
            (29, 'Depot B (South)', 'Zone D (Torrance)', 5.0, 'Normal'),
            (30, 'Depot B (South)', 'Zone G (Long Beach)', 8.0, 'Normal'),
            (31, 'Depot B (South)', 'Zone T (Carson)', 4.0, 'Normal'),
            (32, 'Depot B (South)', 'Zone U (Gardena)', 6.0, 'Normal'),
            (33, 'Depot C (West)', 'Zone E (Santa Monica)', 6.0, 'Normal'),
            (34, 'Depot C (West)', 'Zone S (Culver City)', 4.0, 'Normal'),
            (35, 'Depot C (West)', 'Zone K (Beverly Hills)', 8.0, 'Normal'),
            (36, 'Depot C (West)', 'Zone L (Inglewood)', 7.0, 'Normal')
        ]
        reset_database_state(zones_list, resources_list, vehicles_list, roads_list)

# Attempt to seed on import
try:
    seed_default_if_empty()
except Exception as e:
    print(f"Error seeding database: {e}", file=sys.stderr)
