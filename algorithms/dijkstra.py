import heapq

class DijkstraRouter:
    # Hazard multipliers to adjust edge weights
    DEFAULT_RISK_MULTIPLIERS = {
        'Normal': 1.0,
        'Damaged': 2.0,
        'Flooded': 3.0,
        'Enemy-Controlled': 8.0,
        'Blocked': 9999.0  # Passability penalty
    }

    @classmethod
    def find_shortest_path(cls, roads, source, destination, risk_multipliers=None, inactive_zones=None):
        """
        Calculates the safest and shortest path from source to destination.
        roads: List of dicts
        source: str
        destination: str
        risk_multipliers: Dict override
        inactive_zones: Set or list of deactivated zone names
        
        Returns:
            path: List of strings (nodes) representing the path
            total_distance: float
            total_effective_weight: float (risk-weighted cost)
            path_risk_levels: List of strings
        """
        multipliers = risk_multipliers or cls.DEFAULT_RISK_MULTIPLIERS
        inactive = set(inactive_zones) if inactive_zones else set()
        
        if source in inactive or destination in inactive:
            return [], 0.0, 0.0, []

        # Build adjacency list
        graph = {}
        for road in roads:
            u = road['source']
            v = road['destination']
            
            # Skip deactivated nodes/edges
            if u in inactive or v in inactive:
                continue
                
            dist = road['distance_km']
            risk = road['risk_level']
            mult = multipliers.get(risk, 1.0)
            weight = dist * mult

            if u not in graph:
                graph[u] = []
            if v not in graph:
                graph[v] = []

            # Assume bi-directional roads
            graph[u].append({'to': v, 'dist': dist, 'weight': weight, 'risk': risk})
            graph[v].append({'to': u, 'dist': dist, 'weight': weight, 'risk': risk})

        # Dijkstra algorithm
        pq = [(0.0, source, [source], 0.0, [])]
        visited = set()

        while pq:
            eff_weight, u, path, dist, risks = heapq.heappop(pq)

            if u == destination:
                return path, round(dist, 2), round(eff_weight, 2), risks

            if u in visited:
                continue
            visited.add(u)

            if u not in graph:
                continue

            for edge in graph[u]:
                v = edge['to']
                edge_dist = edge['dist']
                edge_weight = edge['weight']
                edge_risk = edge['risk']

                if v not in visited:
                    heapq.heappush(pq, (
                        eff_weight + edge_weight,
                        v,
                        path + [v],
                        dist + edge_dist,
                        risks + [edge_risk]
                    ))

        return [], 0.0, 0.0, []

    @classmethod
    def find_shortest_path_multi_depot(cls, roads, depots, destination, risk_multipliers=None, inactive_zones=None):
        """
        Calculates the safest and shortest path from the optimal depot among available depots.
        """
        best_path = []
        best_dist = float('inf')
        best_eff_wt = float('inf')
        best_risks = []
        best_depot = None

        for depot in depots:
            path, dist, eff_wt, risks = cls.find_shortest_path(
                roads, depot, destination, risk_multipliers, inactive_zones
            )
            if path and eff_wt < best_eff_wt:
                best_path = path
                best_dist = dist
                best_eff_wt = eff_wt
                best_risks = risks
                best_depot = depot
                
        return best_path, best_dist, best_eff_wt, best_risks, best_depot
