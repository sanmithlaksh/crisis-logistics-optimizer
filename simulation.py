import math
import time
import random
from algorithms.priority_queue import PriorityHeap, RequestItem
from algorithms.resource_allocation import ResourceAllocationEngine
from algorithms.knapsack import KnapsackOptimizer
from algorithms.dijkstra import DijkstraRouter
from algorithms.branch_bound import BranchBoundAssigner

class SimulationEngine:
    SCENARIOS = {
        'Flood': {
            'description': 'Severe flooding across northern and eastern routes. Clean water and food are critical.',
            'road_modifications': {
                ('Depot A (Central)', 'Zone C (East LA)'): 'Flooded',
                ('Zone A (Glendale)', 'Zone B (Pasadena)'): 'Flooded',
                ('Zone B (Pasadena)', 'Depot A (Central)'): 'Flooded',
                ('Depot B (South)', 'Zone G (Long Beach)'): 'Flooded',
                ('Zone C (East LA)', 'Zone G (Long Beach)'): 'Flooded'
            },
            'requests': [
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Water Crate', 'quantity': 120, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Food Packets', 'quantity': 150, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Medicine', 'quantity': 50, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Fuel Ltrs', 'quantity': 100, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Rescue Gear', 'quantity': 10, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 2, 'zone_name': 'Zone B (Pasadena)', 'resource_type': 'Water Crate', 'quantity': 80, 'severity': 'High', 'population': 18000},
                {'zone_id': 3, 'zone_name': 'Zone C (East LA)', 'resource_type': 'Food Packets', 'quantity': 200, 'severity': 'Medium', 'population': 25000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Water Crate', 'quantity': 100, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 7, 'zone_name': 'Zone G (Long Beach)', 'resource_type': 'Water Crate', 'quantity': 180, 'severity': 'Critical', 'population': 30000},
                {'zone_id': 9, 'zone_name': 'Zone I (Burbank)', 'resource_type': 'Food Packets', 'quantity': 120, 'severity': 'Medium', 'population': 14000}
            ]
        },
        'Earthquake': {
            'description': 'Severe structural damage. Hollywood route blocked. Medical kits and rescue gear are critical.',
            'road_modifications': {
                ('Depot A (Central)', 'Zone F (Hollywood)'): 'Blocked',
                ('Zone F (Hollywood)', 'Zone K (Beverly Hills)'): 'Blocked',
                ('Zone D (Torrance)', 'Zone E (Santa Monica)'): 'Damaged',
                ('Depot C (West)', 'Zone E (Santa Monica)'): 'Damaged',
                ('Zone E (Santa Monica)', 'Zone H (Malibu)'): 'Blocked'
            },
            'requests': [
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Medicine', 'quantity': 80, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Rescue Gear', 'quantity': 15, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Food Packets', 'quantity': 150, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Water Crate', 'quantity': 100, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Fuel Ltrs', 'quantity': 50, 'severity': 'Critical', 'population': 15000},
                {'zone_id': 6, 'zone_name': 'Zone F (Hollywood)', 'resource_type': 'Medicine', 'quantity': 100, 'severity': 'Critical', 'population': 22000},
                {'zone_id': 8, 'zone_name': 'Zone H (Malibu)', 'resource_type': 'Rescue Gear', 'quantity': 10, 'severity': 'Low', 'population': 8000},
                {'zone_id': 11, 'zone_name': 'Zone K (Beverly Hills)', 'resource_type': 'Medicine', 'quantity': 60, 'severity': 'Medium', 'population': 9000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Emergency Personnel', 'quantity': 10, 'severity': 'High', 'population': 12000}
            ]
        },
        'Cyclone': {
            'description': 'High winds. Coastal routes blocked. Food, water, and emergency personnel are critical.',
            'road_modifications': {
                ('Depot C (West)', 'Zone E (Santa Monica)'): 'Blocked',
                ('Zone E (Santa Monica)', 'Zone F (Hollywood)'): 'Blocked',
                ('Zone C (East LA)', 'Zone D (Torrance)'): 'Damaged',
                ('Zone E (Santa Monica)', 'Zone K (Beverly Hills)'): 'Blocked'
            },
            'requests': [
                {'zone_id': 5, 'zone_name': 'Zone E (Santa Monica)', 'resource_type': 'Food Packets', 'quantity': 200, 'severity': 'Critical', 'population': 10000},
                {'zone_id': 5, 'zone_name': 'Zone E (Santa Monica)', 'resource_type': 'Water Crate', 'quantity': 150, 'severity': 'Critical', 'population': 10000},
                {'zone_id': 5, 'zone_name': 'Zone E (Santa Monica)', 'resource_type': 'Medicine', 'quantity': 80, 'severity': 'Critical', 'population': 10000},
                {'zone_id': 5, 'zone_name': 'Zone E (Santa Monica)', 'resource_type': 'Fuel Ltrs', 'quantity': 100, 'severity': 'Critical', 'population': 10000},
                {'zone_id': 5, 'zone_name': 'Zone E (Santa Monica)', 'resource_type': 'Rescue Gear', 'quantity': 15, 'severity': 'Critical', 'population': 10000},
                {'zone_id': 11, 'zone_name': 'Zone K (Beverly Hills)', 'resource_type': 'Food Packets', 'quantity': 100, 'severity': 'Medium', 'population': 9000},
                {'zone_id': 3, 'zone_name': 'Zone C (East LA)', 'resource_type': 'Water Crate', 'quantity': 120, 'severity': 'High', 'population': 25000},
                {'zone_id': 4, 'zone_name': 'Zone D (Torrance)', 'resource_type': 'Food Packets', 'quantity': 180, 'severity': 'High', 'population': 15000},
                {'zone_id': 7, 'zone_name': 'Zone G (Long Beach)', 'resource_type': 'Water Crate', 'quantity': 150, 'severity': 'Critical', 'population': 30000}
            ]
        },
        'War Zone': {
            'description': 'Active conflict in Glendale and Hollywood. High risk of route closures. Fuel and medicine are critical.',
            'road_modifications': {
                ('Depot A (Central)', 'Zone A (Glendale)'): 'Enemy-Controlled',
                ('Zone F (Hollywood)', 'Zone A (Glendale)'): 'Enemy-Controlled',
                ('Depot A (Central)', 'Zone F (Hollywood)'): 'Blocked',
                ('Zone A (Glendale)', 'Zone I (Burbank)'): 'Enemy-Controlled'
            },
            'requests': [
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Medicine', 'quantity': 60, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Fuel Ltrs', 'quantity': 100, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Food Packets', 'quantity': 150, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Water Crate', 'quantity': 100, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 1, 'zone_name': 'Zone A (Glendale)', 'resource_type': 'Rescue Gear', 'quantity': 10, 'severity': 'Critical', 'population': 12000},
                {'zone_id': 9, 'zone_name': 'Zone I (Burbank)', 'resource_type': 'Medicine', 'quantity': 50, 'severity': 'Medium', 'population': 14000},
                {'zone_id': 2, 'zone_name': 'Zone B (Pasadena)', 'resource_type': 'Fuel Ltrs', 'quantity': 80, 'severity': 'High', 'population': 18000},
                {'zone_id': 10, 'zone_name': 'Zone J (Anaheim)', 'resource_type': 'Fuel Ltrs', 'quantity': 150, 'severity': 'High', 'population': 35000}
            ]
        }
    }

    @classmethod
    def get_modified_roads(cls, base_roads, scenario_name):
        """Returns the list of roads modified for a specific scenario, preserving the more severe risk levels."""
        scenario = cls.SCENARIOS.get(scenario_name)
        if not scenario:
            return base_roads

        mods = scenario['road_modifications']
        modified = []
        for road in base_roads:
            rd = dict(road)
            pair1 = (rd['source'], rd['destination'])
            pair2 = (rd['destination'], rd['source'])
            
            db_risk = rd.get('risk_level', 'Normal')
            scenario_risk = None
            if pair1 in mods:
                scenario_risk = mods[pair1]
            elif pair2 in mods:
                scenario_risk = mods[pair2]
                
            if scenario_risk:
                db_mult = DijkstraRouter.DEFAULT_RISK_MULTIPLIERS.get(db_risk, 1.0)
                sc_mult = DijkstraRouter.DEFAULT_RISK_MULTIPLIERS.get(scenario_risk, 1.0)
                if sc_mult > db_mult:
                    rd['risk_level'] = scenario_risk
            modified.append(rd)
        return modified

    @classmethod
    def spread_disaster_bfs(cls, zones, roads, num_spreads=3):
        """
        BFS algorithm to spread severity to neighboring zones.
        """
        active_zones = [z for z in zones if z['is_active'] and not z['is_depot']]
        if not active_zones:
            return []

        # Start queue with zones currently ranked Critical or High
        queue = []
        severity_map = {z['name']: z['severity'] for z in zones}
        
        for z in active_zones:
            if z['severity'] in ('Critical', 'High'):
                queue.append(z['name'])

        # If no Critical/High zones exist, start from a random active zone
        if not queue:
            random_zone = random.choice(active_zones)
            queue.append(random_zone['name'])

        visited = set(queue)
        spread_count = 0
        newly_affected = []

        # Build adjacency list
        adj = {}
        for r in roads:
            u, v = r['source'], r['destination']
            if u not in adj: adj[u] = []
            if v not in adj: adj[v] = []
            adj[u].append(v)
            adj[v].append(u)

        while queue and spread_count < num_spreads:
            curr = queue.pop(0)
            if curr not in adj:
                continue

            for neighbor in adj[curr]:
                # Skip depots and deactivated zones
                n_zone = next((z for z in zones if z['name'] == neighbor), None)
                if not n_zone or n_zone['is_depot'] or not n_zone['is_active']:
                    continue

                if neighbor not in visited:
                    curr_sev = severity_map.get(neighbor, 'Low')
                    next_sev = 'Medium'
                    if curr_sev == 'Medium':
                        next_sev = 'High'
                    elif curr_sev == 'High' or curr_sev == 'Critical':
                        next_sev = 'Critical'

                    severity_map[neighbor] = next_sev
                    visited.add(neighbor)
                    newly_affected.append({'id': n_zone['id'], 'name': neighbor, 'severity': next_sev})
                    spread_count += 1
                    queue.append(neighbor)
                    
                    if spread_count >= num_spreads:
                        break

        return newly_affected

    @classmethod
    def run_simulation(cls, scenario_name, base_zones, base_resources, base_vehicles, base_roads):
        scenario = cls.SCENARIOS.get(scenario_name)
        if not scenario:
            return None

        # 1. Modify roads and requests based on scenario
        modified_roads = cls.get_modified_roads(base_roads, scenario_name)
        
        # Filter active zones and depots
        active_zones = [z for z in base_zones if z['is_active']]
        active_zone_names = {z['name'] for z in active_zones}
        inactive_zone_names = {z['name'] for z in base_zones if not z['is_active']}
        active_depot_names = [z['name'] for z in active_zones if z['is_depot']]
        if not active_depot_names:
            active_depot_names = ['Depot A (Central)']

        requests_list = []
        for i, req in enumerate(scenario['requests']):
            if req['zone_name'] in active_zone_names:
                req_copy = dict(req)
                req_copy['request_id'] = 100 + i
                requests_list.append(req_copy)

        initial_inventory = {r['resource_name']: r['available_quantity'] for r in base_resources}
        resource_details = {r['resource_name']: r for r in base_resources}

        # --- Proposed Method Pipeline & Execution Profiling ---
        stats = {
            'heap_ops': 0,
            'dijkstra_ops': 0,
            'bb_nodes': 0,
            'exec_time_ms': 0.0
        }

        t_start = time.perf_counter()

        # 1. Priority Queue Ranks Requests
        heap = PriorityHeap()
        for req in requests_list:
            item = RequestItem(
                req['request_id'], req['zone_id'], req['zone_name'],
                req['resource_type'], req['quantity'], req['severity'], req['population']
            )
            heap.push(item)
            stats['heap_ops'] += 1

        ranked_requests = []
        while heap.size() > 0:
            ranked_requests.append(heap.pop().__dict__)
            stats['heap_ops'] += 1

        # 2. Greedy Allocation Engine
        allocations_prop, updated_inv_prop = ResourceAllocationEngine.allocate_resources(
            ranked_requests, initial_inventory
        )

        # Group allocations by zone for vehicle assignment
        zones_with_res = {}
        for alloc in allocations_prop:
            if alloc['status'] in ('Allocated', 'Partial') and alloc['allocated_quantity'] > 0:
                z_id = alloc['zone_id']
                z_name = alloc['zone_name']
                if z_id not in zones_with_res:
                    zones_with_res[z_id] = {'zone_id': z_id, 'zone_name': z_name, 'resources': []}
                
                res_meta = resource_details[alloc['resource_type']]
                zones_with_res[z_id]['resources'].append({
                    'resource_name': alloc['resource_type'],
                    'quantity': alloc['allocated_quantity'],
                    'unit_weight': res_meta['unit_weight'],
                    'utility_value': res_meta['utility_value']
                })
        
        zones_with_res_list = list(zones_with_res.values())

        # 3. Branch and Bound Vehicle Assignment
        assignments_prop = []
        if zones_with_res_list:
            assignments_prop, bb_details = BranchBoundAssigner.solve_assignment(
                base_vehicles, zones_with_res_list, modified_roads, DijkstraRouter,
                depots=active_depot_names, inactive_zones=inactive_zone_names
            )
            stats['dijkstra_ops'] += len(base_vehicles) * len(zones_with_res_list) * len(active_depot_names)
            stats['bb_nodes'] += len(bb_details)
        else:
            # All vehicles idle
            for v in base_vehicles:
                assignments_prop.append({
                    'vehicle_id': v['vehicle_id'], 'vehicle_name': v['name'], 'vehicle_type': v['type'],
                    'assigned_zone': 'Idle', 'zone_id': None, 'path': [], 'distance_km': 0.0,
                    'travel_time_min': 0.0, 'travel_cost': 0.0, 'risk_penalty': 0.0, 'capacity_penalty': 0.0,
                    'total_cost': 0.0, 'loaded_resources': {}, 'left_behind_resources': {}, 'risks': [], 'optimal_depot': None
                })

        stats['exec_time_ms'] = round((time.perf_counter() - t_start) * 1000.0, 3)

        # Compute Metrics for Proposed
        total_dist_prop = 0.0
        total_time_prop = 0.0
        success_count_prop = 0
        total_dispatches_prop = 0
        delivered_units_prop = 0
        requested_units_total = sum(r['quantity'] for r in requests_list)

        for assign in assignments_prop:
            if assign['assigned_zone'] != 'Idle':
                total_dispatches_prop += 1
                total_dist_prop += assign['distance_km']
                total_time_prop += assign['travel_time_min']
                
                # Check if route is safe
                if 'Blocked' not in assign['risks']:
                    success_count_prop += 1
                    delivered_units_prop += sum(assign['loaded_resources'].values())

        avg_response_prop = (total_time_prop + (total_dispatches_prop * 5.0)) / max(total_dispatches_prop, 1)

        # --- Traditional FCFS Method Pipeline ---
        allocations_trad = []
        current_inv_trad = dict(initial_inventory)
        for req in requests_list:
            res_type = req['resource_type']
            requested_qty = req['quantity']
            available_qty = current_inv_trad.get(res_type, 0)
            allocated_qty = 0
            status = 'Unfulfilled'

            if available_qty > 0:
                if requested_qty <= available_qty:
                    allocated_qty = requested_qty
                    current_inv_trad[res_type] -= requested_qty
                    status = 'Allocated'
                else:
                    allocated_qty = available_qty
                    current_inv_trad[res_type] = 0
                    status = 'Partial'
            
            allocations_trad.append({
                'request_id': req['request_id'], 'zone_id': req['zone_id'], 'zone_name': req['zone_name'],
                'resource_type': res_type, 'requested_quantity': requested_qty, 'allocated_quantity': allocated_qty, 'status': status
            })

        zones_with_res_trad = {}
        for alloc in allocations_trad:
            if alloc['status'] in ('Allocated', 'Partial') and alloc['allocated_quantity'] > 0:
                z_id = alloc['zone_id']
                z_name = alloc['zone_name']
                if z_id not in zones_with_res_trad:
                    zones_with_res_trad[z_id] = {'zone_id': z_id, 'zone_name': z_name, 'resources': []}
                
                res_meta = resource_details[alloc['resource_type']]
                zones_with_res_trad[z_id]['resources'].append({
                    'resource_name': alloc['resource_type'], 'quantity': alloc['allocated_quantity'],
                    'unit_weight': res_meta['unit_weight'], 'utility_value': res_meta['utility_value']
                })
        
        zones_with_res_trad_list = list(zones_with_res_trad.values())

        assignments_trad = []
        vehicles_available = list(base_vehicles)
        static_multipliers = {'Normal': 1.0, 'Damaged': 1.0, 'Flooded': 1.0, 'Enemy-Controlled': 1.0, 'Blocked': 1.0}

        for idx, zone in enumerate(zones_with_res_trad_list):
            if idx < len(vehicles_available):
                vehicle = vehicles_available[idx]
                zone_name = zone['zone_name']
                
                # FCFS always starts from the first depot 'Depot A (Central)'
                path, distance, _, risks = DijkstraRouter.find_shortest_path(
                    modified_roads, 'Depot A (Central)', zone_name, risk_multipliers=static_multipliers, inactive_zones=inactive_zone_names
                )
                
                travel_time = (distance / vehicle['speed_kmh']) * 60.0 if vehicle['speed_kmh'] > 0 and path else 0.0
                
                # Simple FCFS loading
                loaded_items = {}
                left_behind = {}
                curr_wt = 0.0
                for res in zone['resources']:
                    name = res['resource_name']
                    qty = res['quantity']
                    w = res['unit_weight']
                    
                    if w == 0.0:
                        loaded_items[name] = qty
                        continue

                    loaded_qty = 0
                    for _ in range(qty):
                        if curr_wt + w <= vehicle['capacity_weight']:
                            loaded_qty += 1
                            curr_wt += w
                        else:
                            break
                    
                    if loaded_qty > 0:
                        loaded_items[name] = loaded_qty
                    if qty - loaded_qty > 0:
                        left_behind[name] = qty - loaded_qty

                # Mark route failed if path crosses blocked road
                is_blocked = 'Blocked' in risks

                assignments_trad.append({
                    'vehicle_id': vehicle['vehicle_id'], 'vehicle_name': vehicle['name'], 'vehicle_type': vehicle['type'],
                    'assigned_zone': zone_name, 'path': path, 'distance_km': distance, 'travel_time_min': travel_time,
                    'loaded_resources': loaded_items, 'is_failed': is_blocked, 'risks': risks
                })

        total_dist_trad = 0.0
        total_time_trad = 0.0
        success_count_trad = 0
        total_dispatches_trad = 0
        delivered_units_trad = 0

        for assign in assignments_trad:
            total_dispatches_trad += 1
            total_dist_trad += assign['distance_km']
            if assign['is_failed']:
                total_time_trad += 180.0
            else:
                total_time_trad += assign['travel_time_min']
                success_count_trad += 1
                delivered_units_trad += sum(assign['loaded_resources'].values())

        avg_response_trad = (total_time_trad + (total_dispatches_trad * 30.0)) / max(total_dispatches_trad, 1)

        # Aggregate final comparisons
        metrics = {
            'scenario': scenario_name,
            'description': scenario['description'],
            'requested_units': requested_units_total,
            'stats': stats,
            'traditional': {
                'avg_response_time_min': round(avg_response_trad, 2),
                'total_distance_km': round(total_dist_trad, 2),
                'resource_utilization_pct': round((delivered_units_trad / max(requested_units_total, 1)) * 100, 2),
                'success_rate_pct': round((success_count_trad / max(total_dispatches_trad, 1)) * 100, 2) if total_dispatches_trad > 0 else 0.0,
                'requests_served': success_count_trad,
                'dispatches': assignments_trad
            },
            'proposed': {
                'avg_response_time_min': round(avg_response_prop, 2),
                'total_distance_km': round(total_dist_prop, 2),
                'resource_utilization_pct': round((delivered_units_prop / max(requested_units_total, 1)) * 100, 2),
                'success_rate_pct': round((success_count_prop / max(total_dispatches_prop, 1)) * 100, 2) if total_dispatches_prop > 0 else 0.0,
                'requests_served': success_count_prop,
                'dispatches': assignments_prop
            }
        }

        return metrics
