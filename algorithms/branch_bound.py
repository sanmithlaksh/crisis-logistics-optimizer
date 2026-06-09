import copy
from algorithms.knapsack import KnapsackOptimizer

class BranchBoundAssigner:
    @classmethod
    def calculate_assignment_matrix(cls, vehicles, zones_with_resources, roads, router, depots, inactive_zones=None):
        """
        Computes a cost matrix where cost[i][j] is the cost of assigning Vehicle i to Zone j.
        Includes travel cost, road risk, and capacity penalty (undelivered resource utility).
        Uses multi-depot pathfinding to find the optimal depot source.
        """
        matrix = []
        assignment_details = {}

        for i, vehicle in enumerate(vehicles):
            vehicle_rows = []
            for j, zone in enumerate(zones_with_resources):
                zone_name = zone['zone_name']
                allocated_res = zone['resources']

                # 1. Route Cost using Multi-Depot Dijkstra
                path, distance, risk_weight, risks, optimal_depot = router.find_shortest_path_multi_depot(
                    roads, depots, zone_name, inactive_zones=inactive_zones
                )

                if not path or risk_weight >= 9999.0:
                    # Unreachable route
                    travel_cost = 99999.0
                    risk_penalty = 99999.0
                    knapsack_details = {
                        'loaded': {}, 'weight': 0.0, 'utility': 0, 'left_behind': {}
                    }
                    capacity_penalty = 99999.0
                    optimal_depot = None
                else:
                    travel_cost = distance * vehicle['cost_per_km']
                    # Travel risk penalty
                    risk_penalty = risk_weight * 2.5 
                    
                    # 2. Knapsack details for capacity constraint
                    loaded, wt, utility, left_behind = KnapsackOptimizer.optimize_loading(
                        allocated_res, vehicle['capacity_weight']
                    )
                    knapsack_details = {
                        'loaded': loaded,
                        'weight': wt,
                        'utility': utility,
                        'left_behind': left_behind
                    }
                    
                    # Calculate penalty for left-behind resources:
                    capacity_penalty = 0
                    for res in allocated_res:
                        name = res['resource_name']
                        left_qty = left_behind.get(name, 0)
                        capacity_penalty += left_qty * res['utility_value']

                total_cost = travel_cost + risk_penalty + capacity_penalty
                vehicle_rows.append(total_cost)

                assignment_details[(i, j)] = {
                    'path': path,
                    'distance_km': distance,
                    'travel_time_min': round((distance / vehicle['speed_kmh']) * 60.0, 2) if vehicle['speed_kmh'] > 0 and path else 0.0,
                    'travel_cost': round(travel_cost, 2),
                    'risk_penalty': round(risk_penalty, 2),
                    'capacity_penalty': capacity_penalty,
                    'total_cost': round(total_cost, 2),
                    'knapsack': knapsack_details,
                    'risks': risks,
                    'optimal_depot': optimal_depot
                }
            matrix.append(vehicle_rows)

        return matrix, assignment_details

    @classmethod
    def solve_assignment(cls, vehicles, zones_with_resources, roads, router, depots=None, inactive_zones=None):
        """
        Solves the assignment problem using Branch and Bound.
        Finds vehicle-to-zone allocation that minimizes total cost.
        """
        if not vehicles or not zones_with_resources:
            return [], {}

        if not depots:
            # Dynamically identify depots from the roads list if not provided
            possible_depots = set()
            for r in roads:
                if 'Depot' in r['source']:
                    possible_depots.add(r['source'])
                if 'Depot' in r['destination']:
                    possible_depots.add(r['destination'])
            if possible_depots:
                depots = list(possible_depots)
            else:
                depots = ['Depot A (Central)']

        cost_matrix, details = cls.calculate_assignment_matrix(
            vehicles, zones_with_resources, roads, router, depots, inactive_zones
        )

        num_vehicles = len(vehicles)
        num_zones = len(zones_with_resources)

        # Precompute zone default penalties (if not assigned to any vehicle)
        zone_penalties = []
        for zone in zones_with_resources:
            penalty = sum(r['quantity'] * r['utility_value'] for r in zone['resources'])
            zone_penalties.append(penalty)

        best_cost = sum(zone_penalties) # Starting baseline cost (everything unassigned)
        best_assignment = [-1] * num_vehicles # index j of zone assigned to vehicle i (-1 = idle)

        # Helper to compute lower bound for a partial assignment
        def compute_lower_bound(vehicle_idx, assigned_zones):
            lb = 0
            unassigned_zones = set(range(num_zones)) - assigned_zones
            remaining_vehicles_count = num_vehicles - vehicle_idx
            
            if len(unassigned_zones) > remaining_vehicles_count:
                sorted_penalties = sorted([zone_penalties[z] for z in unassigned_zones])
                left_behind_count = len(unassigned_zones) - remaining_vehicles_count
                lb += sum(sorted_penalties[-left_behind_count:])

            for v_id in range(vehicle_idx, num_vehicles):
                min_v_cost = 0
                opts = [cost_matrix[v_id][z] for z in unassigned_zones if cost_matrix[v_id][z] < 99999.0]
                if opts:
                    min_v_cost = min(opts)
                lb += min(min_v_cost, 0)
                
            return lb

        def branch_and_bound(vehicle_idx, current_assignment, current_cost, assigned_zones):
            nonlocal best_cost, best_assignment

            # Base case: all vehicles assigned
            if vehicle_idx == num_vehicles:
                total_cost = current_cost
                for z in range(num_zones):
                    if z not in assigned_zones:
                        total_cost += zone_penalties[z]
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_assignment = copy.deepcopy(current_assignment)
                return

            lb = compute_lower_bound(vehicle_idx, assigned_zones)
            if current_cost + lb >= best_cost:
                return # Prune!

            # Branch 1: Try assigning vehicle_idx to each unassigned zone
            for zone_idx in range(num_zones):
                if zone_idx not in assigned_zones:
                    assign_cost = cost_matrix[vehicle_idx][zone_idx]
                    if assign_cost < 99999.0: # Only assign if reachable
                        new_assignment = list(current_assignment)
                        new_assignment[vehicle_idx] = zone_idx
                        new_assigned_zones = set(assigned_zones)
                        new_assigned_zones.add(zone_idx)
                        
                        branch_and_bound(
                            vehicle_idx + 1, 
                            new_assignment, 
                            current_cost + assign_cost, 
                            new_assigned_zones
                        )

            # Branch 2: Keep vehicle_idx idle
            new_assignment = list(current_assignment)
            new_assignment[vehicle_idx] = -1
            branch_and_bound(
                vehicle_idx + 1, 
                new_assignment, 
                current_cost, 
                assigned_zones
            )

        # Start search
        branch_and_bound(0, [-1] * num_vehicles, 0, set())

        # Formulate results
        results = []
        for v_idx, z_idx in enumerate(best_assignment):
            vehicle = vehicles[v_idx]
            if z_idx != -1:
                zone = zones_with_resources[z_idx]
                det = details[(v_idx, z_idx)]
                results.append({
                    'vehicle_id': vehicle['vehicle_id'],
                    'vehicle_name': vehicle['name'],
                    'vehicle_type': vehicle['type'],
                    'assigned_zone': zone['zone_name'],
                    'zone_id': zone['zone_id'],
                    'path': det['path'],
                    'distance_km': det['distance_km'],
                    'travel_time_min': det['travel_time_min'],
                    'travel_cost': det['travel_cost'],
                    'risk_penalty': det['risk_penalty'],
                    'capacity_penalty': det['capacity_penalty'],
                    'total_cost': det['total_cost'],
                    'loaded_resources': det['knapsack']['loaded'],
                    'left_behind_resources': det['knapsack']['left_behind'],
                    'risks': det['risks'],
                    'optimal_depot': det['optimal_depot']
                })
            else:
                results.append({
                    'vehicle_id': vehicle['vehicle_id'],
                    'vehicle_name': vehicle['name'],
                    'vehicle_type': vehicle['type'],
                    'assigned_zone': 'Idle',
                    'zone_id': None,
                    'path': [],
                    'distance_km': 0.0,
                    'travel_time_min': 0.0,
                    'travel_cost': 0.0,
                    'risk_penalty': 0.0,
                    'capacity_penalty': 0.0,
                    'total_cost': 0.0,
                    'loaded_resources': {},
                    'left_behind_resources': {},
                    'risks': [],
                    'optimal_depot': None
                })

        return results, details
