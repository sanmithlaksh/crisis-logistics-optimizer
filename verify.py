import sys
from algorithms.priority_queue import PriorityHeap, RequestItem
from algorithms.resource_allocation import ResourceAllocationEngine
from algorithms.knapsack import KnapsackOptimizer
from algorithms.dijkstra import DijkstraRouter
from algorithms.branch_bound import BranchBoundAssigner

def test_priority_queue():
    print("Testing Priority Queue (Heap)...")
    heap = PriorityHeap()
    
    # Create request items
    # Priority = Severity Weight + Population Weight + Urgency Weight
    # Glendale: Critical (10) + 2*log10(12000) (~8.16) + Water Crate (8.5) = ~26.66
    r1 = RequestItem(1, 1, 'Glendale', 'Water Crate', 10, 'Critical', 12000)
    # Santa Monica: Low (1) + 2*log10(10000) (8.0) + Food Packets (7.0) = 16.0
    r2 = RequestItem(2, 5, 'Santa Monica', 'Food Packets', 20, 'Low', 10000)
    # Pasadena: High (7) + 2*log10(18000) (~8.51) + Medicine (10.0) = ~25.51
    r3 = RequestItem(3, 2, 'Pasadena', 'Medicine', 5, 'High', 18000)

    heap.push(r1)
    heap.push(r2)
    heap.push(r3)
    
    # Assert heap pops highest score first
    # Expected order: r1 (~26.66), r3 (~25.51), r2 (16.0)
    pop1 = heap.pop()
    pop2 = heap.pop()
    pop3 = heap.pop()
    
    assert pop1.request_id == 1, f"Expected 1, got {pop1.request_id}"
    assert pop2.request_id == 3, f"Expected 3, got {pop2.request_id}"
    assert pop3.request_id == 2, f"Expected 2, got {pop3.request_id}"
    
    print("  Priority Queue tests passed successfully.")

def test_greedy_allocation():
    print("Testing Greedy Resource Allocation...")
    requests = [
        {'request_id': 1, 'zone_id': 1, 'zone_name': 'Glendale', 'resource_type': 'Medicine', 'quantity': 100, 'severity': 'Critical', 'population': 12000},
        {'request_id': 2, 'zone_id': 2, 'zone_name': 'Pasadena', 'resource_type': 'Medicine', 'quantity': 150, 'severity': 'High', 'population': 18000}
    ]
    # Medicine in stock = 120 (r1 gets 100 fully, r2 gets 20 partially)
    initial_inventory = {'Medicine': 120}
    
    allocations, updated_inv = ResourceAllocationEngine.allocate_resources(requests, initial_inventory)
    
    # Assertions
    # Glendale has higher priority (Critical vs High), so it gets medicine first.
    g_alloc = next(a for a in allocations if a['zone_name'] == 'Glendale')
    p_alloc = next(a for a in allocations if a['zone_name'] == 'Pasadena')
    
    assert g_alloc['allocated_quantity'] == 100, f"Expected 100, got {g_alloc['allocated_quantity']}"
    assert g_alloc['status'] == 'Allocated'
    
    assert p_alloc['allocated_quantity'] == 20, f"Expected 20, got {p_alloc['allocated_quantity']}"
    assert p_alloc['status'] == 'Partial'
    
    assert updated_inv['Medicine'] == 0
    print("  Greedy Allocation tests passed successfully.")

def test_knapsack_optimization():
    print("Testing Knapsack Vehicle Cargo Loading (DP)...")
    allocated = [
        {'resource_name': 'Medicine', 'quantity': 10, 'unit_weight': 2.0, 'utility_value': 100}, # total wt = 20, val = 1000
        {'resource_name': 'Water Crate', 'quantity': 15, 'unit_weight': 5.0, 'utility_value': 50}  # total wt = 75, val = 750
    ]
    # Total weight is 95 kg. Vehicle capacity is 50 kg.
    # Knapsack needs to choose the highest value combination.
    # Medicine is way more valuable per unit of weight (100 value / 2kg = 50 value/kg)
    # vs Water Crate (50 value / 5kg = 10 value/kg).
    # So Knapsack should prioritize loading Medicine first!
    # Max medicine loaded = 10 units (weight = 20kg, value = 1000)
    # Remaining weight capacity = 30kg. Fits 6 Water Crates (weight = 30kg, value = 300)
    # Total utility should be 1300, weight = 50.0kg.
    capacity = 50.0
    
    loaded, total_wt, total_util, left_behind = KnapsackOptimizer.optimize_loading(allocated, capacity)
    
    assert loaded['Medicine'] == 10, f"Expected 10 medicine, got {loaded.get('Medicine')}"
    assert loaded['Water Crate'] == 6, f"Expected 6 water, got {loaded.get('Water Crate')}"
    assert total_wt == 50.0, f"Expected weight 50.0, got {total_wt}"
    assert total_util == 1300, f"Expected utility 1300, got {total_util}"
    assert left_behind['Water Crate'] == 9, f"Expected 9 water left behind, got {left_behind.get('Water Crate')}"
    
    print("  Knapsack Optimization tests passed successfully.")

def test_dijkstra_routing():
    print("Testing Dijkstra Route Optimization & Hazard Redirection...")
    # Setup graph
    # Depot -> A = 10 km (Normal)
    # Depot -> B = 8 km (Blocked)
    # B -> A = 2 km (Normal)
    # A -> C = 5 km (Normal)
    # Depot -> C = 15 km (Normal)
    roads = [
        {'source': 'Depot', 'destination': 'A', 'distance_km': 10.0, 'risk_level': 'Normal'},
        {'source': 'Depot', 'destination': 'B', 'distance_km': 8.0, 'risk_level': 'Blocked'},
        {'source': 'B', 'destination': 'A', 'distance_km': 2.0, 'risk_level': 'Normal'},
        {'source': 'A', 'destination': 'C', 'distance_km': 5.0, 'risk_level': 'Normal'},
        {'source': 'Depot', 'destination': 'C', 'distance_km': 15.0, 'risk_level': 'Normal'}
    ]
    
    # 1. Test finding path to C.
    # Shortest physical route is Depot -> B -> A -> C (8 + 2 + 5 = 15 km) but Depot -> B is Blocked (weight multiplier = 9999).
    # Safe route is Depot -> A -> C (10 + 5 = 15 km) or Depot -> C (15 km).
    # Let's check which path Dijkstra picks.
    path, dist, eff_wt, risks = DijkstraRouter.find_shortest_path(roads, 'Depot', 'C')
    
    # Path should not contain 'B' since Depot -> B is Blocked
    assert 'B' not in path, f"Path {path} should not contain B"
    assert path == ['Depot', 'A', 'C'] or path == ['Depot', 'C'], f"Unexpected path {path}"
    assert dist == 15.0
    print("  Dijkstra Routing tests passed successfully.")

def test_branch_bound():
    print("Testing Branch and Bound Vehicle Assignment...")
    vehicles = [
        {'vehicle_id': 1, 'name': 'Truck Alpha', 'type': 'Truck', 'capacity_weight': 100.0, 'speed_kmh': 50.0, 'cost_per_km': 5.0, 'status': 'Available'},
        {'vehicle_id': 2, 'name': 'Drone Beta', 'type': 'Drone', 'capacity_weight': 10.0, 'speed_kmh': 80.0, 'cost_per_km': 1.0, 'status': 'Available'}
    ]
    zones_with_res = [
        {
            'zone_id': 1,
            'zone_name': 'A',
            'resources': [{'resource_name': 'Medicine', 'quantity': 10, 'unit_weight': 2.0, 'utility_value': 100}] # weight = 20kg
        }
    ]
    roads = [
        {'source': 'Depot', 'destination': 'A', 'distance_km': 10.0, 'risk_level': 'Normal'}
    ]
    
    # Solving assignments:
    # A needs 20kg of cargo.
    # - Truck Alpha: Capacity = 100kg. Can carry all 20kg (left-behind penalty = 0). Cost = 10km * 5.0 = $50.
    # - Drone Beta: Capacity = 10kg. Can carry only 5 units of medicine (10kg). Left behind = 5 units (penalty = 5 * 100 = 500 utility points penalty). Cost = 10km * 1.0 + 500 = $510.
    # Thus, Branch & Bound should assign Truck Alpha to Zone A, and Drone Beta should remain Idle!
    assignments, _ = BranchBoundAssigner.solve_assignment(vehicles, zones_with_res, roads, DijkstraRouter)
    
    truck_assign = next(a for a in assignments if a['vehicle_name'] == 'Truck Alpha')
    drone_assign = next(a for a in assignments if a['vehicle_name'] == 'Drone Beta')
    
    assert truck_assign['assigned_zone'] == 'A', f"Expected Truck assigned to A, got {truck_assign['assigned_zone']}"
    assert drone_assign['assigned_zone'] == 'Idle', f"Expected Drone Idle, got {drone_assign['assigned_zone']}"
    
    print("  Branch & Bound tests passed successfully.")

if __name__ == '__main__':
    print("=== STARTING ALGORITHM VERIFICATION TESTS ===")
    try:
        test_priority_queue()
        test_greedy_allocation()
        test_knapsack_optimization()
        test_dijkstra_routing()
        test_branch_bound()
        print("=== ALL ALGORITHMIC CHECKS PASSED SUCCESSFULLY! ===")
        sys.exit(0)
    except AssertionError as e:
        print(f"!!! TEST ASSERTION FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"!!! ERROR DURING TESTING: {e}")
        sys.exit(1)
