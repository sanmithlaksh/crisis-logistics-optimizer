#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <stdbool.h>

#define MAX_ZONES 6
#define MAX_RESOURCES 5
#define MAX_VEHICLES 3
#define INF 99999

#define MAX_ITEMS 15
#define MAX_CAPACITY 1000

/* --- 1. DATA STRUCTURE DEFINITIONS --- */

typedef struct {
    int request_id;
    char zone_name[30];
    int zone_idx;
    char resource_type[30];
    int quantity;
    int severity_weight; /* Critical = 3, High = 2, Medium = 1, Low = 0 */
    int population;
    double priority_score;
} Request;

typedef struct {
    Request data[50];
    int size;
} MaxHeap;

typedef struct {
    char name[30];
    int available_qty;
    double unit_weight;
    int utility_value;
} Resource;

typedef struct {
    int vehicle_id;
    char name[30];
    double capacity_weight;
    double speed;
    double cost_per_km;
    int assigned_zone_idx; /* -1 if Idle */
} Vehicle;

typedef struct {
    int source;
    int dest;
    double distance;
    char risk_level[20]; /* Normal, Flooded, Blocked */
} Road;

/* Node names map for console output */
const char* ZONE_NAMES[MAX_ZONES] = {
    "Depot", 
    "Zone A (Glendale)", 
    "Zone B (Pasadena)", 
    "Zone C (East LA)", 
    "Zone D (Torrance)", 
    "Zone E (Santa Monica)"
};

/* --- 2. MAX-HEAP PRIORITY QUEUE --- */

double calculate_priority(int severity_weight, int population) {
    return (severity_weight * 10.0) + (population / 10000.0);
}

void swap_requests(Request *a, Request *b) {
    Request temp = *a;
    *a = *b;
    *b = temp;
}

void heap_push(MaxHeap *heap, Request req) {
    heap->data[heap->size] = req;
    int i = heap->size;
    heap->size++;
    
    /* Heapify up */
    while (i > 0 && heap->data[i].priority_score > heap->data[(i - 1) / 2].priority_score) {
        swap_requests(&heap->data[i], &heap->data[(i - 1) / 2]);
        i = (i - 1) / 2;
    }
}

Request heap_pop(MaxHeap *heap) {
    Request root = heap->data[0];
    heap->size--;
    heap->data[0] = heap->data[heap->size];
    
    int i = 0;
    /* Heapify down */
    while (2 * i + 1 < heap->size) {
        int largest = 2 * i + 1;
        int right = 2 * i + 2;
        if (right < heap->size && heap->data[right].priority_score > heap->data[largest].priority_score) {
            largest = right;
        }
        if (heap->data[i].priority_score >= heap->data[largest].priority_score) {
            break;
        }
        swap_requests(&heap->data[i], &heap->data[largest]);
        i = largest;
    }
    return root;
}

/* --- Helper: Print Total Requests Done by Each Zone --- */
void print_total_requests_by_zone(Request requests[], int req_count) {
    printf("--- SUMMARIZING DEMAND: Total Requests Done by Zone ---\n");
    int zone_totals[MAX_ZONES] = {0};
    
    for (int i = 0; i < req_count; i++) {
        zone_totals[requests[i].zone_idx] += requests[i].quantity;
    }
    
    for (int i = 1; i < MAX_ZONES; i++) {
        printf("  %s: Total requested units = %d\n", ZONE_NAMES[i], zone_totals[i]);
    }
    printf("\n");
}

/* --- 3. GREEDY RESOURCE ALLOCATION --- */

void allocate_resources(MaxHeap *heap, Resource *inventory, int inv_size) {
    printf("--- DEMO 2: Greedy Resource Allocation ---\n");
    
    /* Temporary heap copy for popping requests */
    MaxHeap temp_heap = *heap;
    
    while (temp_heap.size > 0) {
        Request req = heap_pop(&temp_heap);
        
        /* Find resource in inventory */
        int res_idx = -1;
        for (int i = 0; i < inv_size; i++) {
            if (strcmp(inventory[i].name, req.resource_type) == 0) {
                res_idx = i;
                break;
            }
        }
        
        if (res_idx != -1) {
            int allocated = 0;
            int requested = req.quantity;
            int available = inventory[res_idx].available_qty;
            
            if (available >= requested) {
                allocated = requested;
                inventory[res_idx].available_qty -= requested;
                printf("  Allocated fully: %d units of %s to %s (Status: Allocated)\n", 
                       allocated, req.resource_type, req.zone_name);
            } else if (available > 0) {
                allocated = available;
                inventory[res_idx].available_qty = 0;
                printf("  Allocated partially: %d/%d units of %s to %s (Status: Partial)\n", 
                       allocated, requested, req.resource_type, req.zone_name);
            } else {
                printf("  Unfulfilled: 0/%d units of %s to %s (Status: Unfulfilled - Stock Depleted)\n", 
                       requested, req.resource_type, req.zone_name);
            }
        }
    }
    printf("\n");
}

/* --- 4. RISK-WEIGHTED DIJKSTRA ROUTING --- */

double get_hazard_multiplier(const char* risk_level) {
    if (strcmp(risk_level, "Blocked") == 0) return 9999.0;
    if (strcmp(risk_level, "Flooded") == 0) return 3.0;
    return 1.0; /* Normal */
}

void dijkstra(double graph[MAX_ZONES][MAX_ZONES], double risk_graph[MAX_ZONES][MAX_ZONES], 
              int start, int dest, int *path, int *path_len, double *out_dist, double *out_eff_wt) {
    double dist[MAX_ZONES];
    double eff_wt[MAX_ZONES];
    int parent[MAX_ZONES];
    bool visited[MAX_ZONES] = {false};
    
    for (int i = 0; i < MAX_ZONES; i++) {
        dist[i] = INF;
        eff_wt[i] = INF;
        parent[i] = -1;
    }
    
    dist[start] = 0;
    eff_wt[start] = 0;
    
    for (int count = 0; count < MAX_ZONES - 1; count++) {
        /* Find min effective weight node */
        double min_eff = INF;
        int u = -1;
        for (int v = 0; v < MAX_ZONES; v++) {
            if (!visited[v] && eff_wt[v] <= min_eff) {
                min_eff = eff_wt[v];
                u = v;
            }
        }
        
        if (u == -1) break;
        visited[u] = true;
        
        /* Update neighbors */
        for (int v = 0; v < MAX_ZONES; v++) {
            if (!visited[v] && graph[u][v] != 0 && eff_wt[u] != INF) {
                double edge_eff_wt = graph[u][v] * risk_graph[u][v];
                if (eff_wt[u] + edge_eff_wt < eff_wt[v]) {
                    eff_wt[v] = eff_wt[u] + edge_eff_wt;
                    dist[v] = dist[u] + graph[u][v];
                    parent[v] = u;
                }
            }
        }
    }
    
    *out_dist = dist[dest];
    *out_eff_wt = eff_wt[dest];
    
    /* Reconstruct path */
    int temp_path[MAX_ZONES];
    int count = 0;
    int curr = dest;
    while (curr != -1) {
        temp_path[count++] = curr;
        curr = parent[curr];
    }
    
    *path_len = count;
    for (int i = 0; i < count; i++) {
        path[i] = temp_path[count - 1 - i];
    }
}

/* --- 5. 0/1 KNAPSACK DYNAMIC PROGRAMMING --- */

void knapsack_optimize(int hold_capacity_scaled, int weights_scaled[], int values[], int items_count, 
                       int selected_counts[], int *total_value, int *total_weight_scaled, const char* item_names[]) {
    static int dp[MAX_ITEMS + 1][MAX_CAPACITY + 1];
    
    if (items_count > MAX_ITEMS) items_count = MAX_ITEMS;
    if (hold_capacity_scaled > MAX_CAPACITY) hold_capacity_scaled = MAX_CAPACITY;
    
    /* Dynamic programming grid population */
    for (int i = 0; i <= items_count; i++) {
        for (int w = 0; w <= hold_capacity_scaled; w++) {
            if (i == 0 || w == 0) {
                dp[i][w] = 0;
            } else if (weights_scaled[i - 1] <= w) {
                int take = values[i - 1] + dp[i - 1][w - weights_scaled[i - 1]];
                int skip = dp[i - 1][w];
                dp[i][w] = (take > skip) ? take : skip;
            } else {
                dp[i][w] = dp[i - 1][w];
            }
        }
    }
    
    *total_value = dp[items_count][hold_capacity_scaled];
    
    /* Backtrack to identify selected items and output the maximization calculation details */
    int w = hold_capacity_scaled;
    *total_weight_scaled = 0;
    
    printf("\n--- Step-by-Step Backtracking & Maximization Calculations ---\n");
    printf("Capacity = %.1f kg (Scaled: %d)\n", hold_capacity_scaled / 10.0, hold_capacity_scaled);
    
    for (int i = items_count; i > 0; i--) {
        int item_wt = weights_scaled[i - 1];
        int item_val = values[i - 1];
        
        if (w >= item_wt) {
            int val_if_taken = item_val + dp[i - 1][w - item_wt];
            int val_if_skipped = dp[i - 1][w];
            
            /* The core maximization decision check */
            if (dp[i][w] == val_if_taken && dp[i][w] != dp[i - 1][w]) {
                selected_counts[i - 1] = 1;
                *total_weight_scaled += item_wt;
                printf("  [Item %2d] %-15s (Weight: %3.1f kg, Value: %3d) -> SELECTED\n", 
                       i, item_names[i - 1], item_wt / 10.0, item_val);
                printf("    * Decision Reason: Value if taken (%d) > Value if skipped (%d).\n", 
                       val_if_taken, val_if_skipped);
                printf("    * Calculation: dp[%d][%d] = max(dp[%d][%d], %d + dp[%d][%d]) = %d\n", 
                       i, w, i - 1, w, item_val, i - 1, w - item_wt, dp[i][w]);
                printf("    * Capacity decreases: %.1f kg -> %.1f kg\n", w / 10.0, (w - item_wt) / 10.0);
                w -= item_wt;
            } else {
                selected_counts[i - 1] = 0;
                printf("  [Item %2d] %-15s (Weight: %3.1f kg, Value: %3d) -> SKIPPED\n", 
                       i, item_names[i - 1], item_wt / 10.0, item_val);
                printf("    * Decision Reason: Value if skipped (%d) >= Value if taken (%d).\n", 
                       val_if_skipped, val_if_taken);
                printf("    * Calculation: dp[%d][%d] = max(dp[%d][%d], %d + dp[%d][%d]) = %d\n", 
                       i, w, i - 1, w, item_val, i - 1, w - item_wt, dp[i][w]);
            }
        } else {
            selected_counts[i - 1] = 0;
            printf("  [Item %2d] %-15s (Weight: %3.1f kg, Value: %3d) -> SKIPPED\n", 
                   i, item_names[i - 1], item_wt / 10.0, item_val);
            printf("    * Decision Reason: Item weight exceeds remaining capacity of %.1f kg.\n", w / 10.0);
        }
    }
}

/* --- 6. BRANCH AND BOUND DISPATCH SOLVER --- */

double best_bb_cost = INF;
int best_bb_assignment[MAX_VEHICLES]; /* maps vehicle index to zone index */

void solve_bb_recursion(int vehicle_idx, int current_assignment[], double current_cost, 
                         bool assigned_zones[], double cost_matrix[MAX_VEHICLES][MAX_ZONES]) {
    /* Base Case */
    if (vehicle_idx == MAX_VEHICLES) {
        if (current_cost < best_bb_cost) {
            best_bb_cost = current_cost;
            for (int i = 0; i < MAX_VEHICLES; i++) {
                best_bb_assignment[i] = current_assignment[i];
            }
        }
        return;
    }
    
    /* Branch 1: Try assigning vehicle to each zone */
    for (int z = 1; z < MAX_ZONES; z++) { /* Skip 0 (Depot) */
        if (!assigned_zones[z]) {
            double assign_cost = cost_matrix[vehicle_idx][z];
            if (assign_cost < INF) {
                assigned_zones[z] = true;
                current_assignment[vehicle_idx] = z;
                
                /* Recursive call */
                solve_bb_recursion(vehicle_idx + 1, current_assignment, current_cost + assign_cost, 
                                   assigned_zones, cost_matrix);
                
                /* Backtrack */
                assigned_zones[z] = false;
                current_assignment[vehicle_idx] = -1;
            }
        }
    }
}

/* --- 7. MAIN RUN EXECUTION --- */

int main() {
    printf("=========================================================\n");
    printf("  CRISIS LOGISTICS OPTIMIZER - DAA ALGORITHM SUITE DEMO  \n");
    printf("=========================================================\n\n");
    
    /* --- DATA INITIALIZATION --- */
    
    /* Initialize requests */
    int num_requests = 6;
    Request requests[6] = {
        {101, "Zone A (Glendale)", 1, "Water Crate", 120, 3, 12000, 0.0},
        {102, "Zone E (Santa Monica)", 5, "Medicine", 50, 0, 10000, 0.0},
        {103, "Zone D (Torrance)", 4, "Fuel Ltrs", 80, 2, 15000, 0.0},
        {104, "Zone B (Pasadena)", 2, "Rescue Gear", 10, 1, 18000, 0.0},
        {105, "Zone A (Glendale)", 1, "Medicine", 30, 3, 12000, 0.0},
        {106, "Zone D (Torrance)", 4, "Water Crate", 50, 2, 15000, 0.0}
    };
    
    /* Calculate priority scores for all requests */
    for (int i = 0; i < num_requests; i++) {
        requests[i].priority_score = calculate_priority(requests[i].severity_weight, requests[i].population);
    }
    
    /* Print the total requests done by each zone */
    print_total_requests_by_zone(requests, num_requests);
    
    /* --- DEMO 1: MAX-HEAP SORTING --- */
    printf("--- DEMO 1: Max-Heap Priority Ranking ---\n");
    MaxHeap heap;
    heap.size = 0;
    
    for (int i = 0; i < num_requests; i++) {
        heap_push(&heap, requests[i]);
    }
    
    printf("Requests pushed into Max-Heap. Popping in prioritized order:\n");
    for (int i = 0; i < num_requests; i++) {
        Request popped = heap_pop(&heap);
        printf("  Rank %d: %-22s | Item: %-12s | Score: %5.2f (Severity Wt: %d, Pop: %d)\n", 
               i + 1, popped.zone_name, popped.resource_type, popped.priority_score, 
               popped.severity_weight, popped.population);
    }
    printf("\n");
    
    /* Rebuild heap for Allocation Demo */
    heap.size = 0;
    for (int i = 0; i < num_requests; i++) {
        heap_push(&heap, requests[i]);
    }
    
    /* Warehouse Stocks */
    Resource inventory[MAX_RESOURCES] = {
        {"Water Crate", 150, 5.0, 50}, /* Stock: 150 (Req: 120 + 50 -> Glendale gets 120, Torrance gets 30 (Partial)) */
        {"Medicine", 500, 2.0, 100},   /* Stock: 500 (Req: 50 + 30 -> both fully fulfilled) */
        {"Fuel Ltrs", 60, 3.0, 70},    /* Stock: 60 (Req: 80 -> Torrance gets 60 (Partial)) */
        {"Rescue Gear", 5, 15.0, 90}   /* Stock: 5 (Req: 10 -> Pasadena gets 5 (Partial)) */
    };
    
    /* Run Greedy Allocation */
    allocate_resources(&heap, inventory, MAX_RESOURCES - 1);
    
    /* --- DEMO 3: RISK-WEIGHTED DIJKSTRA --- */
    printf("--- DEMO 3: Risk-Weighted Dijkstra Routing ---\n");
    /* Graph Setup: distances in km */
    double graph[MAX_ZONES][MAX_ZONES] = {
        /* D,  A,  B,  C,  D,  E */
        {0.0, 10.5, 0.0, 8.2, 0.0, 0.0},  /* Depot (0) */
        {10.5, 0.0, 9.2, 0.0, 0.0, 0.0},  /* Zone A (1) */
        {0.0, 9.2, 0.0, 14.5, 0.0, 0.0},  /* Zone B (2) */
        {8.2, 0.0, 14.5, 0.0, 27.1, 0.0}, /* Zone C (3) */
        {0.0, 0.0, 0.0, 27.1, 0.0, 28.5}, /* Zone D (4) */
        {0.0, 0.0, 0.0, 0.0, 28.5, 0.0}   /* Zone E (5) */
    };
    
    /* Road risk status settings */
    double risk_graph[MAX_ZONES][MAX_ZONES];
    for (int i = 0; i < MAX_ZONES; i++) {
        for (int j = 0; j < MAX_ZONES; j++) {
            risk_graph[i][j] = 1.0;
        }
    }
    
    /* Block path Glendale (1) <-> Pasadena (2) to demonstrate detour routing */
    risk_graph[1][2] = get_hazard_multiplier("Blocked");
    risk_graph[2][1] = get_hazard_multiplier("Blocked");
    
    /* Flood path Depot (0) <-> East LA (3) */
    risk_graph[0][3] = get_hazard_multiplier("Flooded");
    risk_graph[3][0] = get_hazard_multiplier("Flooded");
    
    printf("Simulating: Glendale <-> Pasadena is BLOCKED; Depot <-> East LA is FLOODED.\n");
    printf("Finding safest path from Depot to Pasadena:\n");
    
    int path[MAX_ZONES];
    int path_len = 0;
    double distance = 0;
    double eff_wt = 0;
    
    dijkstra(graph, risk_graph, 0, 2, path, &path_len, &distance, &eff_wt);
    
    printf("  Safe Path found: ");
    for (int i = 0; i < path_len; i++) {
        printf("%s", ZONE_NAMES[path[i]]);
        if (i < path_len - 1) printf(" -> ");
    }
    printf("\n  Physical Distance: %.2f km | Dijkstra Effective Risk-Weighted Cost: %.2f\n\n", distance, eff_wt);
    
    /* --- DEMO 4: 0/1 KNAPSACK WITH 12 ITEMS --- */
    printf("--- DEMO 4: 0/1 Knapsack Cargo Hold Optimization (12 Items) ---\n");
    
    /* 12 items cargo options database */
    const char* item_names[12] = {
        "Medicine A", "Food Pack A", "Water Pack A", "Fuel Ltrs A",
        "Rescue Gear A", "Medicine B", "Food Pack B", "Water Pack B",
        "Fuel Ltrs B", "Blankets", "First Aid Kit", "Flashlights"
    };
    /* Weights in kg (multiplied by 10 to make integers for DP array indexes) */
    int item_weights_scaled[12] = {
        20,   /* Medicine A: 2.0 kg */
        15,   /* Food Pack A: 1.5 kg */
        50,   /* Water Pack A: 5.0 kg */
        30,   /* Fuel Ltrs A: 3.0 kg */
        120,  /* Rescue Gear A: 12.0 kg */
        10,   /* Medicine B: 1.0 kg */
        20,   /* Food Pack B: 2.0 kg */
        40,   /* Water Pack B: 4.0 kg */
        25,   /* Fuel Ltrs B: 2.5 kg */
        35,   /* Blankets: 3.5 kg */
        8,    /* First Aid Kit: 0.8 kg */
        5     /* Flashlights: 0.5 kg */
    };
    int item_values[12] = {
        100,  /* Medicine A */
        45,   /* Food Pack A */
        60,   /* Water Pack A */
        80,   /* Fuel Ltrs A */
        150,  /* Rescue Gear A */
        50,   /* Medicine B */
        50,   /* Food Pack B */
        40,   /* Water Pack B */
        65,   /* Fuel Ltrs B */
        35,   /* Blankets */
        40,   /* First Aid Kit */
        25    /* Flashlights */
    };
    
    /* Vehicle Capacity: 15.0 kg -> 150 scaled weight */
    int hold_capacity_scaled = 150; 
    
    int selected_counts[12] = {0};
    int total_value = 0;
    int total_weight_scaled = 0;
    
    knapsack_optimize(hold_capacity_scaled, item_weights_scaled, item_values, 12, 
                      selected_counts, &total_value, &total_weight_scaled, item_names);
    
    printf("\n--- Summary of Items Packed in Hold (Target: Maximize Value) ---\n");
    int count_selected = 0;
    for (int i = 0; i < 12; i++) {
        if (selected_counts[i] == 1) {
            count_selected++;
            double percentage_contrib = (item_values[i] / (double)total_value) * 100.0;
            printf("  Loaded: %-15s | Weight: %3.1f kg | Value: %3d | Value Contribution: %5.1f%%\n", 
                   item_names[i], item_weights_scaled[i] / 10.0, item_values[i], percentage_contrib);
        }
    }
    
    printf("\n  Summary statistics:\n");
    printf("    * Total Selected Items: %d out of 12 items\n", count_selected);
    printf("    * Capacity Fulfilling Rate: %.1f%% (%.1f / 15.0 kg)\n", 
           (total_weight_scaled / (double)hold_capacity_scaled) * 100.0, total_weight_scaled / 10.0);
    printf("    * Total Cargo Utility Value: %d points\n\n", total_value);
    
    /* --- DEMO 5: BRANCH AND BOUND DECISION MATRIX --- */
    printf("--- DEMO 5: Branch and Bound Vehicle Assignment ---\n");
    /* Matrix layout: cost[vehicle][zone]. Row 0 = Truck, Row 1 = Heli, Row 2 = Drone */
    double cost_matrix[MAX_VEHICLES][MAX_ZONES] = {
        /* D,  A(1), B(2), C(3), D(4), E(5) */
        {0, 50.5,  120.0, 40.2,  INF,   INF},   /* Vehicle 0 (Truck Alpha) */
        {0, 110.2, 90.0,  180.0, 320.0, INF},   /* Vehicle 1 (Rescue Heli) */
        {0, 20.0,  55.0,  INF,   INF,   90.0}   /* Vehicle 2 (Aid Drone) */
    };
    
    int current_assignment[MAX_VEHICLES] = {-1, -1, -1};
    bool assigned_zones[MAX_ZONES] = {false};
    
    best_bb_cost = INF;
    for (int i = 0; i < MAX_VEHICLES; i++) best_bb_assignment[i] = -1;
    
    solve_bb_recursion(0, current_assignment, 0.0, assigned_zones, cost_matrix);
    
    printf("Optimal fleet matching solved via Branch and Bound search tree:\n");
    for (int i = 0; i < MAX_VEHICLES; i++) {
        int z_idx = best_bb_assignment[i];
        if (z_idx != -1) {
            printf("  Assign Vehicle %d to %s (Cost: $%.2f)\n", 
                   i, ZONE_NAMES[z_idx], cost_matrix[i][z_idx]);
        } else {
            printf("  Keep Vehicle %d Idle (Cost: $0.00)\n", i);
        }
    }
    printf("  Total Fleet Dispatch Cost: $%.2f\n\n", best_bb_cost);
    
    printf("=========================================================\n");
    printf("             ALL DAA ALGORITHMS COMPLETED                \n");
    printf("=========================================================\n");
    return 0;
}
