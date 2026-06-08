class KnapsackOptimizer:
    @staticmethod
    def optimize_loading(allocated_resources, capacity_weight):
        """
        Applies 0/1 Knapsack to select resources that maximize utility within capacity.
        allocated_resources: List of dicts, each with {
            'resource_name': str,
            'quantity': int,
            'unit_weight': float,
            'utility_value': int
        }
        capacity_weight: float (Vehicle capacity)

        Returns:
            loaded_items: Dict of {resource_name: quantity} representing what got loaded
            total_loaded_weight: float
            total_utility: int
            left_behind: Dict of {resource_name: quantity} representing what did not fit
        """
        # Convert quantities to individual items
        # To handle float weights, we scale them by 10 (e.g., 2.5 kg -> 25)
        scale_factor = 10
        int_capacity = int(round(capacity_weight * scale_factor))
        
        # Flatten allocated resources into individual units
        flat_items = []
        zero_weight_items = []  # items with weight = 0 can be loaded for free (like personnel)

        for res in allocated_resources:
            name = res['resource_name']
            qty = res['quantity']
            w = res['unit_weight']
            val = res['utility_value']

            if w == 0.0:
                zero_weight_items.append((name, qty, val))
                continue

            for _ in range(qty):
                flat_items.append({
                    'name': name,
                    'weight_scaled': int(round(w * scale_factor)),
                    'weight_orig': w,
                    'value': val
                })

        n = len(flat_items)
        if n == 0:
            # Check zero-weight items
            loaded = {}
            total_utility = 0
            for name, qty, val in zero_weight_items:
                loaded[name] = qty
                total_utility += val * qty
            return loaded, 0.0, total_utility, {}

        # DP table initialization
        # dp[i][w] stores max value with first i items and capacity w
        dp = [[0] * (int_capacity + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            item = flat_items[i - 1]
            wt = item['weight_scaled']
            val = item['value']
            for w in range(int_capacity + 1):
                if wt <= w:
                    dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - wt] + val)
                else:
                    dp[i][w] = dp[i - 1][w]

        # Backtracking to find selected items
        loaded_flat = []
        w = int_capacity
        for i in range(n, 0, -1):
            # If value came from dp[i-1][w-wt] + val, item i-1 was selected
            item = flat_items[i - 1]
            wt = item['weight_scaled']
            val = item['value']
            
            # Use floating point safety check and make sure index is valid
            if w >= wt and dp[i][w] != dp[i - 1][w] and dp[i][w] == dp[i - 1][w - wt] + val:
                loaded_flat.append(item)
                w -= wt

        # Aggregate loaded items
        loaded_items = {}
        total_loaded_weight = 0.0
        total_utility = 0

        # Load zero-weight items first (always loaded for free)
        for name, qty, val in zero_weight_items:
            loaded_items[name] = qty
            total_utility += val * qty

        for item in loaded_flat:
            name = item['name']
            loaded_items[name] = loaded_items.get(name, 0) + 1
            total_loaded_weight += item['weight_orig']
            total_utility += item['value']

        # Determine left-behind items
        left_behind = {}
        for res in allocated_resources:
            name = res['resource_name']
            total_qty = res['quantity']
            loaded_qty = loaded_items.get(name, 0)
            diff = total_qty - loaded_qty
            if diff > 0:
                left_behind[name] = diff

        return loaded_items, round(total_loaded_weight, 2), total_utility, left_behind
