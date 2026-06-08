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
    def find_shortest_path(cls, roads, source, destination, risk_multipliers=None):
        """
        Calculates the safest and shortest path from source to destination.
        roads: List of dicts, each with {
            'source': str,
            'destination': str,
            'distance_km': float,
            'risk_level': str
        }
        source: str
        destination: str
        risk_multipliers: Dict override for risk multipliers
        
        Returns:
            path: List of strings (nodes) representing the path
            total_distance: float
            total_effective_weight: float (risk-weighted cost)
            path_risk_levels: List of strings representing risk level of each traversed road
        """
        multipliers = risk_multipliers or cls.DEFAULT_RISK_MULTIPLIERS
        
        # Build adjacency list
        graph = {}
        for road in roads:
            u = road['source']
            v = road['destination']
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
        # min-heap stores: (cumulative_weight, current_node, path_so_far, cumulative_distance, risk_list)
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

        # Return empty if unreachable
        return [], 0.0, 0.0, []
