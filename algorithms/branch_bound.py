import copy
from algorithms.knapsack import KnapsackOptimizer

class BranchBoundAssigner:
    @staticmethod
    def calculate_assignment_matrix(vehicles, zones_with_resources, roads, router):
        """
        Computes a cost matrix where cost[i][j] is the cost of assigning Vehicle i to Zone j.
        Includes travel cost, road risk, and capacity penalty (undelivered resource utility).
        """
        matrix = []
        # Store metadata about route and knapsack for each potential assignment
        assignment_details = {}

        for i, vehicle in enumerate(vehicles):
            vehicle_rows = []
            for j, zone in enumerate(zones_with_resources):
                zone_name = zone['zone_name']
                allocated_res = zone['resources'] # list of resource dicts

                # 1. Route Cost using Dijkstra
                path, distance, risk_weight, risks = router.find_shortest_path(
                    roads, 'Depot', zone_name
                )

                if not path or risk_weight >= 9999.0:
                    # Unreachable route
                    travel_cost = 99999.0
                    risk_penalty = 99999.0
                    knapsack_details = {
                        'loaded': {}, 'weight': 0.0, 'utility': 0, 'left_behind': {}
                    }
                    capacity_penalty = 99999.0
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
                    # Sum of (utility_value * quantity) for left behind items
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
                    'risks': risks
                }
            matrix.append(vehicle_rows)

        return matrix, assignment_details

    @classmethod
    def solve_assignment(cls, vehicles, zones_with_resources, roads, router):
        """
        Solves the assignment problem using Branch and Bound.
        Finds vehicle-to-zone allocation that minimizes total cost.
        """
        if not vehicles or not zones_with_resources:
            return [], {}

        cost_matrix, details = cls.calculate_assignment_matrix(
            vehicles, zones_with_resources, roads, router
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
        # assigned_zones is a set of zone indices already assigned
        def compute_lower_bound(vehicle_idx, assigned_zones):
            lb = 0
            # 1. Add cost of already assigned vehicles (handled in search recursion)
            
            # 2. For unassigned zones that cannot be served by remaining vehicles,
            # they must incur their penalty. Let's estimate conservatively:
            unassigned_zones = set(range(num_zones)) - assigned_zones
            remaining_vehicles_count = num_vehicles - vehicle_idx
            
            if len(unassigned_zones) > remaining_vehicles_count:
                # Some zones must remain unassigned. Take the ones with smallest penalties
                # and assume they are assigned, and the rest (with largest penalties) are unassigned.
                sorted_penalties = sorted([zone_penalties[z] for z in unassigned_zones])
                # Number of zones that must be left behind:
                left_behind_count = len(unassigned_zones) - remaining_vehicles_count
                lb += sum(sorted_penalties[-left_behind_count:])

            # 3. For remaining vehicles, add minimum possible cost from remaining unassigned zones
            for v_id in range(vehicle_idx, num_vehicles):
                min_v_cost = 0
                opts = [cost_matrix[v_id][z] for z in unassigned_zones if cost_matrix[v_id][z] < 99999.0]
                if opts:
                    min_v_cost = min(opts)
                # Ensure we don't underestimate: if it's better to keep vehicle idle, cost is 0,
                # but then the zones remain unassigned (handled in penalty calculation above)
                lb += min(min_v_cost, 0)
                
            return lb

        def branch_and_bound(vehicle_idx, current_assignment, current_cost, assigned_zones):
            nonlocal best_cost, best_assignment

            # Base case: all vehicles assigned
            if vehicle_idx == num_vehicles:
                # Add penalty for any zones that were never assigned
                total_cost = current_cost
                for z in range(num_zones):
                    if z not in assigned_zones:
                        total_cost += zone_penalties[z]
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_assignment = copy.deepcopy(current_assignment)
                return

            # Compute lower bound to decide whether to prune
            lb = compute_lower_bound(vehicle_idx, assigned_zones)
            # Add penalty of zones currently not assigned (conservative estimate)
            unassigned_zones = set(range(num_zones)) - assigned_zones
            current_penalties = sum(zone_penalties[z] for z in unassigned_zones)
            
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
                    'risks': det['risks']
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
                    'risks': []
                })

        return results, details
