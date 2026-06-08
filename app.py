import os
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
        # Get active requests
        reqs = database.get_requests()
        if not reqs:
            return jsonify({'status': 'success', 'allocations': [], 'heap': []})
            
        # Get current depot inventory
        inventory_rows = database.get_resources()
        inventory = {r['resource_name']: r['available_quantity'] for r in inventory_rows}
        
        # Build heap and calculate rankings
        heap = PriorityHeap()
        for r in reqs:
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
        
        # Run allocation
        allocations, updated_inventory = ResourceAllocationEngine.allocate_resources(
            reqs, inventory
        )
        
        # Update database with allocation status and decrement resources
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

@app.route('/api/simulate/<scenario>', methods=['POST'])
def run_scenario_simulation(scenario):
    try:
        if scenario not in SimulationEngine.SCENARIOS:
            return jsonify({'status': 'error', 'message': f'Scenario {scenario} not found'}), 400
            
        # Read from database
        zones = database.get_zones()
        resources = database.get_resources()
        vehicles = database.get_vehicles()
        roads = database.get_roads()
        
        # Run simulation
        results = SimulationEngine.run_simulation(
            scenario, zones, resources, vehicles, roads
        )
        
        return jsonify({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_database():
    try:
        # Re-seed with defaults
        database.USING_SQLITE_FALLBACK = True if not os.getenv('SUPABASE_URL') else database.USING_SQLITE_FALLBACK
        
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
            (11, 'Zone K (Beverly Hills)', 34.0736, -118.4004, 9000, 'Medium')
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
            (3, 'Depot', 'Zone F (Hollywood)', 9.0, 'Normal'),
            (4, 'Depot', 'Zone D (Torrance)', 25.4, 'Normal'),
            (5, 'Depot', 'Zone E (Santa Monica)', 24.1, 'Normal'),
            (6, 'Zone A (Glendale)', 'Zone B (Pasadena)', 9.2, 'Normal'),
            (7, 'Zone B (Pasadena)', 'Zone C (East LA)', 14.5, 'Normal'),
            (8, 'Zone C (East LA)', 'Zone D (Torrance)', 27.1, 'Normal'),
            (9, 'Zone D (Torrance)', 'Zone E (Santa Monica)', 28.5, 'Normal'),
            (10, 'Zone E (Santa Monica)', 'Zone F (Hollywood)', 15.2, 'Normal'),
            (11, 'Zone F (Hollywood)', 'Zone A (Glendale)', 11.4, 'Normal'),
            (12, 'Zone B (Pasadena)', 'Depot', 16.1, 'Normal'),
            (13, 'Depot', 'Zone K (Beverly Hills)', 12.0, 'Normal'),
            (14, 'Depot', 'Zone G (Long Beach)', 32.0, 'Normal'),
            (15, 'Depot', 'Zone I (Burbank)', 18.0, 'Normal'),
            (16, 'Zone K (Beverly Hills)', 'Zone E (Santa Monica)', 12.5, 'Normal'),
            (17, 'Zone F (Hollywood)', 'Zone K (Beverly Hills)', 6.0, 'Normal'),
            (18, 'Zone D (Torrance)', 'Zone G (Long Beach)', 15.0, 'Normal'),
            (19, 'Zone C (East LA)', 'Zone G (Long Beach)', 28.0, 'Normal'),
            (20, 'Zone E (Santa Monica)', 'Zone H (Malibu)', 25.0, 'Normal'),
            (21, 'Zone A (Glendale)', 'Zone I (Burbank)', 6.5, 'Normal'),
            (22, 'Zone F (Hollywood)', 'Zone I (Burbank)', 8.5, 'Normal'),
            (23, 'Zone C (East LA)', 'Zone J (Anaheim)', 35.0, 'Normal'),
            (24, 'Zone B (Pasadena)', 'Zone J (Anaheim)', 42.0, 'Normal')
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
            
        path, distance, eff_wt, risks = DijkstraRouter.find_shortest_path(
            roads, 'Depot', destination
        )
        
        return jsonify({
            'status': 'success',
            'path': path,
            'distance_km': distance,
            'effective_weight': eff_wt,
            'risks': risks
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Try seeding database before starting Flask
    try:
        database.seed_default_if_empty()
    except Exception as e:
        print(f"Startup database seeding failed: {e}")
        
    app.run(debug=True, port=5000)
