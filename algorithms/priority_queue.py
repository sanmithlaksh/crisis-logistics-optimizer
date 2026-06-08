import heapq
import math

class RequestItem:
    def __init__(self, request_id, zone_id, zone_name, resource_type, quantity, severity, population, base_urgency=None):
        self.request_id = request_id
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.resource_type = resource_type
        self.quantity = quantity
        self.severity = severity
        self.population = population
        
        # Determine resource urgency weight if not provided
        if base_urgency is not None:
            self.urgency = base_urgency
        else:
            self.urgency = self._get_resource_urgency(resource_type)
            
        self.priority_score = self.calculate_priority()

    def _get_resource_urgency(self, resource_type):
        urgencies = {
            'Medicine': 10.0,
            'Emergency Personnel': 9.0,
            'Water Crate': 8.5,
            'Food Packets': 7.0,
            'Rescue Gear': 6.0,
            'Fuel Ltrs': 5.0
        }
        return urgencies.get(resource_type, 5.0)

    def calculate_priority(self):
        # Severity weights
        severity_weights = {
            'Critical': 10.0,
            'High': 7.0,
            'Medium': 4.0,
            'Low': 1.0
        }
        w_sev = severity_weights.get(self.severity, 1.0)
        
        # Population weight: 2 * log10(pop) capped at 10.0
        if self.population > 0:
            w_pop = min(2.0 * math.log10(self.population), 10.0)
        else:
            w_pop = 0.0
            
        # Urgency weight
        w_urg = self.urgency
        
        # Score = w_sev + w_pop + w_urg
        return round(w_sev + w_pop + w_urg, 2)

    # For heapq min-heap to act as max-heap, we compare by negating the score.
    # To resolve ties, we compare by zone name then request ID.
    def __lt__(self, other):
        if self.priority_score == other.priority_score:
            if self.zone_name == other.zone_name:
                return self.request_id < other.request_id
            return self.zone_name < other.zone_name
        return self.priority_score > other.priority_score  # Reversed for max-heap behavior

    def to_dict(self):
        return {
            'request_id': self.request_id,
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'resource_type': self.resource_type,
            'quantity': self.quantity,
            'severity': self.severity,
            'population': self.population,
            'urgency': self.urgency,
            'priority_score': self.priority_score
        }

class PriorityHeap:
    def __init__(self):
        self.heap = []

    def push(self, item: RequestItem):
        heapq.heappush(self.heap, item)

    def pop(self) -> RequestItem:
        if self.is_empty():
            return None
        return heapq.heappop(self.heap)

    def peek(self) -> RequestItem:
        if self.is_empty():
            return None
        return self.heap[0]

    def is_empty(self):
        return len(self.heap) == 0

    def size(self):
        return len(self.heap)

    def get_heap_list(self):
        # Return list representing the heap array layout for tree visualization
        return [item.to_dict() for item in self.heap]
