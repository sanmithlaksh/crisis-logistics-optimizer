import os
import random
import sys
from flask import Flask, jsonify, request, render_template
import database
from simulation import SimulationEngine
from algorithms.priority_queue import PriorityHeap, RequestItem
from algorithms.resource_allocation import ResourceAllocationEngine
from algorithms.branch_bound import BranchBoundAssigner
from algorithms.dijkstra import DijkstraRouter

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_current_data():
    try:
        zones = database.get_zones()
        resources = database.get_resources()
        vehicles = database.get_vehicles()
        roads = database.get_roads()
        requests_data = database.get_requests()
        
        return jsonify({
            'status': 'success',
            'zones': zones,
            'resources': resources,
            'vehicles': vehicles,
            'roads': roads,
            'requests': requests_data,
            'using_sqlite_fallback': database.USING_SQLITE_FALLBACK
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/request', methods=['POST'])
def add_custom_request():
    try:
        data = request.json
        zone_id = int(data['zone_id'])
        resource_type = data['resource_type']
        quantity = int(data['quantity'])
        
        # Look up zone to check severity and population
        zones = database.get_zones()
        zone = next((z for z in zones if z['id'] == zone_id), None)
        if not zone:
            return jsonify({'status': 'error', 'message': 'Zone not found'}), 404
            
        # Calculate priority score
        temp_item = RequestItem(
            request_id=999,
            zone_id=zone_id,
            zone_name=zone['name'],
            resource_type=resource_type,
            quantity=quantity,
            severity=zone['severity'],
            population=zone['population']
        )
        
        database.insert_request(
            zone_id=zone_id,
            resource_type=resource_type,
            quantity=quantity,
            priority=temp_item.priority_score,
            status='Pending'
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Request added successfully',
            'priority_score': temp_item.priority_score
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/allocate', methods=['POST'])
def run_live_allocation():
    try:
        reqs = database.get_requests()
        if not reqs:
            return jsonify({'status': 'success', 'allocations': [], 'heap': []})
            
        inventory_rows = database.get_resources()
        inventory = {r['resource_name']: r['available_quantity'] for r in inventory_rows}
        
        # Build heap and calculate rankings
        heap = PriorityHeap()
        for r in reqs:
            if r['status'] == 'Pending':
                item = RequestItem(
                    request_id=r['request_id'],
                    zone_id=r['zone_id'],
                    zone_name=r['zone_name'],
                    resource_type=r['resource_type'],
                    quantity=r['quantity'],
                    severity=r['severity'],
                    population=r['population']
                )
                heap.push(item)
            
        heap_list = heap.get_heap_list()
        
        allocations, updated_inventory = ResourceAllocationEngine.allocate_resources(
            reqs, inventory
        )
        
        for alloc in allocations:
            database.update_request_status(alloc['request_id'], alloc['status'])
            
        for name, qty in updated_inventory.items():
            database.update_resource_quantity(name, qty)
            
        return jsonify({
            'status': 'success',
            'allocations': allocations,
            'heap': heap_list,
            'updated_inventory': updated_inventory
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/zone/toggle', methods=['POST'])
def toggle_zone():
    """Toggles active status of a zone, or randomly deactivates one."""
    try:
        data = request.json or {}
        zone_id = data.get('zone_id')
        is_active = data.get('is_active')
        random_deactivate = data.get('random', False)

        zones = database.get_zones()

        if random_deactivate:
            # Get list of active zones that are not depots
            active_zones = [z for z in zones if z['is_active'] and not z['is_depot']]
            if not active_zones:
                return jsonify({'status': 'error', 'message': 'No active zones available to deactivate'}), 400
            target_zone = random.choice(active_zones)
            zone_id = target_zone['id']
            is_active = False
        else:
            if zone_id is None or is_active is None:
                return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400
            target_zone = next((z for z in zones if z['id'] == int(zone_id)), None)

        if not target_zone:
            return jsonify({'status': 'error', 'message': 'Zone not found'}), 404

        database.update_zone_active_status(zone_id, is_active)
        status_str = "Deactivated" if not is_active else "Activated"
        return jsonify({
            'status': 'success',
            'message': f"Zone '{target_zone['name']}' has been {status_str}.",
            'zone_id': zone_id,
            'zone_name': target_zone['name'],
            'is_active': is_active
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/road/hazard', methods=['POST'])
def toggle_road_hazard():
    """Updates a single road hazard level, or applies a scenario preset group."""
    try:
        data = request.json or {}
        source = data.get('source')
        destination = data.get('destination')
        risk_level = data.get('risk_level')
        category = data.get('category')  # Option to toggle a preset category

        if category:
            # Apply presets to set of roads
            presets = {
                'Damaged': [
                    ('Zone A (Glendale)', 'Zone I (Burbank)'),
                    ('Zone C (East LA)', 'Zone M (Downey)'),
                    ('Zone M (Downey)', 'Zone O (Compton)')
                ],
                'Flooded': [
                    ('Depot A (Central)', 'Zone C (East LA)'),
                    ('Depot B (South)', 'Zone G (Long Beach)'),
                    ('Zone C (East LA)', 'Zone D (Torrance)')
                ],
                'Enemy-Controlled': [
                    ('Depot A (Central)', 'Zone A (Glendale)'),
                    ('Zone A (Glendale)', 'Zone F (Hollywood)'),
                    ('Zone F (Hollywood)', 'Zone I (Burbank)')
                ],
                'Blocked': [
                    ('Zone F (Hollywood)', 'Zone K (Beverly Hills)'),
                    ('Zone E (Santa Monica)', 'Zone H (Malibu)'),
                    ('Zone S (Culver City)', 'Zone U (Gardena)')
                ]
            }

            roads_to_mod = presets.get(category, [])
            # If current active level of these is already that category, toggle them to 'Normal'
            roads = database.get_roads()
            first_road = next((r for r in roads if (r['source'] == roads_to_mod[0][0] and r['destination'] == roads_to_mod[0][1]) or 
                                                   (r['source'] == roads_to_mod[0][1] and r['destination'] == roads_to_mod[0][0])), None)
            
            target_level = category
            if first_road and first_road['risk_level'] == category:
                target_level = 'Normal'

            for src, dest in roads_to_mod:
                database.update_road_hazard(src, dest, target_level)

            return jsonify({
                'status': 'success',
                'message': f"Scenario preset '{category}' applied. Status set to: {target_level}."
            })
        
        else:
            if not source or not destination or not risk_level:
                return jsonify({'status': 'error', 'message': 'Missing source, destination, or risk level'}), 400
            
            database.update_road_hazard(source, destination, risk_level)
            return jsonify({
                'status': 'success',
                'message': f"Road '{source} <-> {destination}' updated to {risk_level}."
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/simulate/<scenario>', methods=['POST'])
def run_scenario_simulation(scenario):
    try:
        if scenario not in SimulationEngine.SCENARIOS:
            return jsonify({'status': 'error', 'message': f'Scenario {scenario} not found'}), 400
            
        zones = database.get_zones()
        resources = database.get_resources()
        vehicles = database.get_vehicles()
        roads = database.get_roads()
        
        results = SimulationEngine.run_simulation(
            scenario, zones, resources, vehicles, roads
        )
        
        return jsonify({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/simulate/large', methods=['POST'])
def run_large_disaster():
    """Generates 10 new random crisis zones and random requests, then returns stats."""
    try:
        # Load current data
        zones = database.get_zones()
        roads = database.get_roads()
        
        # Determine starting index for naming
        new_zones_data = []
        new_roads_data = []
        new_requests_data = []
        
        start_id = max(z['id'] for z in zones) + 1
        
        for k in range(10):
            z_id = start_id + k
            z_name = f"Zone X{k+1} (Dynamic)"
            # Bounding box coordinates around LA
            lat = round(random.uniform(33.78, 34.15), 4)
            lng = round(random.uniform(-118.45, -118.05), 4)
            pop = random.randint(5000, 45000)
            sev = random.choice(['Low', 'Medium', 'High', 'Critical'])
            
            new_zones_data.append((z_id, z_name, lat, lng, pop, sev, 1, 0))
            
            # Find closest existing zone to connect road network
            closest_zone = min(zones, key=lambda z: math.sqrt((z['latitude'] - lat)**2 + (z['longitude'] - lng)**2))
            # Calculate distance approx in km (1 degree ~ 111km)
            distance = round(math.sqrt((closest_zone['latitude'] - lat)**2 + (closest_zone['longitude'] - lng)**2) * 111.0, 1)
            if distance < 1.0: distance = 1.2
            
            new_roads_data.append((z_name, closest_zone['name'], distance, 'Normal'))
            
            # Generate 1-2 random requests
            res_choices = ['Medicine', 'Food Packets', 'Water Crate', 'Fuel Ltrs']
            res_type = random.choice(res_choices)
            qty = random.randint(30, 180)
            priority = (10 if sev == 'Critical' else 7 if sev == 'High' else 4 if sev == 'Medium' else 1) * 10 + (pop / 10000.0)
            
            new_requests_data.append((z_id, res_type, qty, priority, 'Pending'))
            
        database.insert_new_zones_bulk(new_zones_data, new_roads_data, new_requests_data)
        
        # Load updated state and run simulation
        zones_upd = database.get_zones()
        resources_upd = database.get_resources()
        vehicles_upd = database.get_vehicles()
        roads_upd = database.get_roads()
        
        # Run simulation using Burbank as active scenario mapping baseline
        results = SimulationEngine.run_simulation(
            'Flood', zones_upd, resources_upd, vehicles_upd, roads_upd
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully generated 10 dynamic zones, roads, and requests.',
            'new_zones_count': len(new_zones_data),
            'total_zones_count': len(zones_upd),
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/simulate/shortage', methods=['POST'])
def run_shortage():
    """Reduces resources stock levels to 10% and runs greedy allocation."""
    try:
        resources = database.get_resources()
        for res in resources:
            reduced_qty = max(10, int(res['available_quantity'] * 0.1))
            database.update_resource_quantity(res['resource_name'], reduced_qty)
            
        # Trigger allocation rerun
        return run_live_allocation()
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/simulate/spread', methods=['POST'])
def run_disaster_spread():
    """BFS disaster spread algorithm that propagates severity and adds requests."""
    try:
        zones = database.get_zones()
        roads = database.get_roads()
        
        newly_affected = SimulationEngine.spread_disaster_bfs(zones, roads, num_spreads=3)
        
        new_requests = []
        for zone in newly_affected:
            # Update severity in DB
            database.update_zone_active_status(zone['id'], True) # make sure active
            
            # Find complete zone details to update severity
            conn = database.get_sqlite_conn() if database.USING_SQLITE_FALLBACK else None
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE zones SET severity = ? WHERE id = ?", (zone['severity'], zone['id']))
                conn.commit()
                conn.close()
            
            # Generate random request
            res_choices = ['Medicine', 'Food Packets', 'Water Crate', 'Fuel Ltrs']
            res_type = random.choice(res_choices)
            qty = random.randint(50, 150)
            
            # Lookup population for score
            z_details = next(z for z in zones if z['id'] == zone['id'])
            priority = (10 if zone['severity'] == 'Critical' else 7 if zone['severity'] == 'High' else 4 if zone['severity'] == 'Medium' else 1) * 10 + (z_details['population'] / 10000.0)
            database.insert_request(zone['id'], res_type, qty, priority, 'Pending')
            new_requests.append({
                'zone_name': zone['name'],
                'severity': zone['severity'],
                'resource_type': res_type,
                'quantity': qty
            })
            
        return jsonify({
            'status': 'success',
            'message': f"Disaster spread to {len(newly_affected)} zones.",
            'spread_zones': newly_affected,
            'new_requests': new_requests
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/simulate/route_failure', methods=['POST'])
def run_route_failure():
    """Simulates a road collapse mid-transit by blocking Glendale <-> Pasadena."""
    try:
        # Block road Glendale <-> Pasadena
        database.update_road_hazard('Zone A (Glendale)', 'Zone B (Pasadena)', 'Blocked')
        
        # Trigger route re-check
        return jsonify({
            'status': 'success',
            'message': "Road collapse simulated: 'Glendale <-> Pasadena' is now BLOCKED.",
            'blocked_road': 'Zone A (Glendale) <-> Zone B (Pasadena)'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_database():
    try:
        database.USING_SQLITE_FALLBACK = True if not os.getenv('SUPABASE_URL') else database.USING_SQLITE_FALLBACK
        
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
        
        database.reset_database_state(zones_list, resources_list, vehicles_list, roads_list)
        return jsonify({'status': 'success', 'message': 'Database successfully reset to default state'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/route_to', methods=['GET'])
def get_route_to():
    try:
        destination = request.args.get('destination')
        scenario = request.args.get('scenario')
        
        roads = database.get_roads()
        if scenario and scenario in SimulationEngine.SCENARIOS:
            roads = SimulationEngine.get_modified_roads(roads, scenario)
            
        zones = database.get_zones()
        inactive_zones = {z['name'] for z in zones if not z['is_active']}
        depots = [z['name'] for z in zones if z['is_depot'] and z['is_active']]
        if not depots:
            depots = ['Depot A (Central)']

        path, distance, eff_wt, risks, optimal_depot = DijkstraRouter.find_shortest_path_multi_depot(
            roads, depots, destination, inactive_zones=inactive_zones
        )
        
        return jsonify({
            'status': 'success',
            'path': path,
            'distance_km': distance,
            'effective_weight': eff_wt,
            'risks': risks,
            'optimal_depot': optimal_depot
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    try:
        database.seed_default_if_empty()
    except Exception as e:
        print(f"Startup database seeding failed: {e}")
        
    app.run(debug=True, port=5000)
