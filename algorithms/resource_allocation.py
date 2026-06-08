from algorithms.priority_queue import PriorityHeap, RequestItem

class ResourceAllocationEngine:
    @staticmethod
    def allocate_resources(requests_list, initial_inventory):
        """
        Greedy allocation algorithm.
        requests_list: List of dicts representing requests, including zone details.
        initial_inventory: Dict of {resource_name: available_quantity}
        
        Returns:
            allocations: List of dicts detail allocation outcomes
            updated_inventory: Dict representing the new inventory state after greedy allocation
        """
        # 1. Initialize Max-Heap
        heap = PriorityHeap()
        for req in requests_list:
            item = RequestItem(
                request_id=req['request_id'],
                zone_id=req['zone_id'],
                zone_name=req['zone_name'],
                resource_type=req['resource_type'],
                quantity=req['quantity'],
                severity=req['severity'],
                population=req['population']
            )
            heap.push(item)

        # Make a deep copy of the inventory
        current_inventory = dict(initial_inventory)
        allocations = []

        # 2. Greedy Loop
        # Process requests in highest priority first
        while not heap.is_empty():
            request_item = heap.pop()
            res_type = request_item.resource_type
            requested_qty = request_item.quantity
            available_qty = current_inventory.get(res_type, 0)

            allocated_qty = 0
            status = 'Unfulfilled'

            if available_qty > 0:
                if requested_qty <= available_qty:
                    # Full allocation
                    allocated_qty = requested_qty
                    current_inventory[res_type] -= requested_qty
                    status = 'Allocated'
                else:
                    # Partial allocation
                    allocated_qty = available_qty
                    current_inventory[res_type] = 0
                    status = 'Partial'
            else:
                status = 'Unfulfilled'

            allocations.append({
                'request_id': request_item.request_id,
                'zone_id': request_item.zone_id,
                'zone_name': request_item.zone_name,
                'resource_type': res_type,
                'requested_quantity': requested_qty,
                'allocated_quantity': allocated_qty,
                'priority_score': request_item.priority_score,
                'status': status
            })

        return allocations, current_inventory
