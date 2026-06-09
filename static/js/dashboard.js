// Global State Variables
let appData = {
    zones: [],
    resources: [],
    vehicles: [],
    roads: [],
    requests: [],
    using_sqlite_fallback: false
};

let activeScenario = null;
let simulationResults = null;

// Tab Configurations
const tabConfig = {
    'tab-inventory': { title: 'Resource Inventory Depot', desc: 'Monitor central supply depot stock levels and manage available resource classes.' },
    'tab-requests': { title: 'Request Queue & Heap Priority', desc: 'Monitor active disaster requests, rank urgency using a Max-Heap, and allocate resources.' },
    'tab-map': { title: 'Hazard-Aware Route Visualizer', desc: 'Dijkstra route optimization finding shortest paths bypassing flooded, blocked, or hostile sectors.' },
    'tab-fleet': { title: 'Fleet Assignment hold capacity', desc: 'View optimal vehicle-to-zone allocations solved via Branch and Bound, and Knapsack vehicle cargo.' },
    'tab-simulation': { title: 'Scenario Simulation & Analytics', desc: 'Compare the efficiency of our AI Engine against traditional FCFS routing under real-world crisis conditions.' },
    'tab-guide': { title: 'System Presentation & DAA Manual', desc: 'Step-by-step demonstration walkthrough guide and theoretical analysis of core DAA algorithms.' }
};

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    setupTabNavigation();
    loadDashboardData();
    setupEventListeners();
    initCharts(); // from charts.js
    initMap();    // from map.js
}

// ==========================================================================
// 1. Tab Navigation
// ==========================================================================
function setupTabNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPages = document.querySelectorAll('.tab-page');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Toggle button states
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle pages
            tabPages.forEach(p => p.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');

            // Update Headers
            const config = tabConfig[targetTab];
            if (config) {
                document.getElementById('current-tab-title').innerText = config.title;
                document.getElementById('current-tab-desc').innerText = config.desc;
            }

            // Perform tab-specific actions
            if (targetTab === 'tab-map') {
                setTimeout(() => {
                    initMap();
                    if (mapInstance) {
                        mapInstance.invalidateSize(); // Reset size for Leaflet container
                        updateMapData(appData.zones, appData.roads, appData.requests);
                    }
                }, 200);
            }
        });
    });
}

// ==========================================================================
// 2. Fetch data from backend API
// ==========================================================================
function loadDashboardData() {
    fetch('/api/data')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                appData = data;
                updateDBModeLabel();
                renderInventory();
                renderRequests();
                renderFleet();
                populateRequestForms();
                
                // Update map if initialized
                if (mapInstance && document.getElementById('tab-map').classList.contains('active')) {
                    updateMapData(appData.zones, appData.roads, appData.requests);
                }
            } else {
                showErrorNotification(data.message);
            }
        })
        .catch(err => showErrorNotification("Failed to fetch dashboard registry: " + err));
}

function updateDBModeLabel() {
    const label = document.getElementById('db-mode-label');
    if (appData.using_sqlite_fallback) {
        label.innerText = "SQLite Mode";
        label.style.color = "#ffd600";
    } else {
        label.innerText = "Supabase Mode";
        label.style.color = "#00e676";
    }
}

// ==========================================================================
// 3. UI Renders
// ==========================================================================

// Tab 1: Render Inventory
function renderInventory() {
    const container = document.getElementById('inventory-list');
    const tableBody = document.getElementById('resource-weights-table');
    container.innerHTML = '';
    tableBody.innerHTML = '';

    // Icons map for resources
    const icons = {
        'Medicine': '<i class="fa-solid fa-kit-medical"></i>',
        'Food Packets': '<i class="fa-solid fa-box-tissue"></i>',
        'Water Crate': '<i class="fa-solid fa-bottle-water"></i>',
        'Fuel Ltrs': '<i class="fa-solid fa-gas-pump"></i>',
        'Rescue Gear': '<i class="fa-solid fa-helmet-safety"></i>',
        'Emergency Personnel': '<i class="fa-solid fa-user-doctor"></i>'
    };

    // Capacity maximums for slider representation
    const maxCaps = {
        'Medicine': 500,
        'Food Packets': 1000,
        'Water Crate': 800,
        'Fuel Ltrs': 400,
        'Rescue Gear': 100,
        'Emergency Personnel': 50
    };

    appData.resources.forEach(res => {
        const icon = icons[res.resource_name] || '<i class="fa-solid fa-box"></i>';
        const maxVal = maxCaps[res.resource_name] || 1000;
        const fillPct = (res.available_quantity / maxVal) * 100;

        // Inventory list cards
        const card = document.createElement('div');
        card.className = 'inventory-card';
        card.innerHTML = `
            <div class="inventory-meta">
                <span class="inv-name">${res.resource_name}</span>
                <div class="inv-icon-container">${icon}</div>
            </div>
            <div class="inv-qty">${res.available_quantity} <span style="font-size:14px; font-weight:500;">units</span></div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${fillPct}%"></div>
            </div>
            <div class="inv-details">
                <span>Weight: ${res.unit_weight} kg</span>
                <span>Max: ${maxVal}</span>
            </div>
        `;
        container.appendChild(card);

        // Weights table
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><b>${res.resource_name}</b></td>
            <td>${res.unit_weight} kg</td>
            <td><span class="badge badge-info">${res.utility_value} pts</span></td>
        `;
        tableBody.appendChild(row);
    });
}

// Tab 2: Render Requests List & populate dropdowns
function renderRequests() {
    const tableBody = document.getElementById('requests-table-body');
    tableBody.innerHTML = '';

    const pendingRequests = appData.requests.filter(r => r.status === 'Pending');
    document.getElementById('stat-active-requests').innerText = pendingRequests.length;

    if (appData.requests.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No active requests. Select a scenario or submit a manual request.</td></tr>`;
        renderHeap([]);
        return;
    }

    // Sort requests by priority score descending for table view
    const sortedRequests = [...appData.requests].sort((a, b) => b.priority - a.priority);

    sortedRequests.forEach(req => {
        let statusBadge = '';
        if (req.status === 'Pending') statusBadge = '<span class="badge badge-warning">Pending</span>';
        else if (req.status === 'Allocated') statusBadge = '<span class="badge badge-success">Allocated</span>';
        else if (req.status === 'Partial') statusBadge = '<span class="badge badge-info">Partial</span>';
        else if (req.status === 'Unfulfilled') statusBadge = '<span class="badge badge-danger">Unfulfilled</span>';

        let sevClass = '';
        if (req.severity === 'Critical') sevClass = 'severity-critical';
        else if (req.severity === 'High') sevClass = 'severity-high';
        else if (req.severity === 'Medium') sevClass = 'severity-medium';
        else if (req.severity === 'Low') sevClass = 'severity-low';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>#${req.request_id}</td>
            <td><b>${req.zone_name}</b> <span class="badge badge-info" style="font-size:8px;">Pop: ${req.population}</span></td>
            <td>${req.resource_type}</td>
            <td>${req.quantity}</td>
            <td><b>${req.priority}</b> <span class="badge badge-warning" style="font-size:8px;">${req.severity}</span></td>
            <td>${statusBadge}</td>
        `;
        tableBody.appendChild(row);
    });

    // Populate Heap Visualizer if we have pending requests
    const heapItems = pendingRequests.map(r => ({
        zone_name: r.zone_name,
        resource_type: r.resource_type,
        priority_score: r.priority
    }));
    
    // Sort array into heap-ordered layout (Max Heap simulation)
    // We can run Heapify structure:
    buildMaxHeap(heapItems);
    renderHeap(heapItems);
}

// Tab 4: Render Fleet list
function renderFleet() {
    const container = document.getElementById('fleet-list');
    container.innerHTML = '';

    appData.vehicles.forEach(vehicle => {
        const card = document.createElement('div');
        card.className = 'fleet-card';
        
        let statusClass = 'available';
        if (vehicle.status === 'Dispatched') statusClass = 'dispatched';
        
        // Find if vehicle is assigned in current simulation
        let assignmentText = '<div class="fleet-assignment-box idle">Idle</div>';
        if (simulationResults && simulationResults.proposed && simulationResults.proposed.dispatches) {
            const assignment = simulationResults.proposed.dispatches.find(d => d.vehicle_id === vehicle.vehicle_id);
            if (assignment && assignment.assigned_zone !== 'Idle') {
                assignmentText = `<div class="fleet-assignment-box">Dispatched to <b>${assignment.assigned_zone}</b></div>`;
                statusClass = 'dispatched';
            }
        }

        card.innerHTML = `
            <div class="fleet-header">
                <div>
                    <span class="fleet-title">${vehicle.name}</span>
                    <div class="fleet-subtitle">${vehicle.type}</div>
                </div>
                <span class="fleet-status-badge ${statusClass}">${vehicle.status}</span>
            </div>
            <div class="fleet-details-row">
                <span>Capacity:</span>
                <span>${vehicle.capacity_weight} kg</span>
            </div>
            <div class="fleet-details-row">
                <span>Speed:</span>
                <span>${vehicle.speed_kmh} km/h</span>
            </div>
            <div class="fleet-details-row">
                <span>Cost/km:</span>
                <span>$${vehicle.cost_per_km.toFixed(2)}</span>
            </div>
            ${assignmentText}
        `;
        container.appendChild(card);
    });
}

function populateRequestForms() {
    const select = document.getElementById('req-zone');
    select.innerHTML = '<option value="" disabled selected>Select affected zone</option>';
    
    appData.zones.forEach(zone => {
        const opt = document.createElement('option');
        opt.value = zone.id;
        opt.innerText = `${zone.name} (${zone.severity})`;
        select.appendChild(opt);
    });
}

// ==========================================================================
// 4. Binary Heap Tree Drawer
// ==========================================================================
function buildMaxHeap(arr) {
    // Standard heapify logic to simulate binary heap array order
    const len = arr.length;
    for (let i = Math.floor(len / 2) - 1; i >= 0; i--) {
        maxHeapify(arr, len, i);
    }
}

function maxHeapify(arr, n, i) {
    let largest = i;
    const left = 2 * i + 1;
    const right = 2 * i + 2;

    if (left < n && arr[left].priority_score > arr[largest].priority_score) {
        largest = left;
    }
    if (right < n && arr[right].priority_score > arr[largest].priority_score) {
        largest = right;
    }

    if (largest !== i) {
        const swap = arr[i];
        arr[i] = arr[largest];
        arr[largest] = swap;
        maxHeapify(arr, n, largest);
    }
}

function renderHeap(heapArray) {
    const visualizer = document.getElementById('heap-tree-visual');
    visualizer.innerHTML = '';

    if (!heapArray || heapArray.length === 0) {
        visualizer.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-network-wired"></i>
                <p>Heap is currently empty. Add requests or load a scenario to visualize the priority queue heap structure.</p>
            </div>
        `;
        return;
    }

    const container = document.createElement('div');
    container.className = 'heap-node-container';

    // Break heap down into levels: 0 (root), 1 (index 1-2), 2 (index 3-6), 3 (index 7-14)
    const totalLevels = Math.ceil(Math.log2(heapArray.length + 1));

    for (let l = 0; l < Math.min(totalLevels, 4); l++) { // Cap rendering at 4 levels for UX UI readability
        const levelDiv = document.createElement('div');
        levelDiv.className = 'heap-level';
        levelDiv.style.justifyContent = 'space-around';

        const startIndex = Math.pow(2, l) - 1;
        const endIndex = Math.min(Math.pow(2, l + 1) - 1, heapArray.length);

        for (let i = startIndex; i < endIndex; i++) {
            const node = heapArray[i];
            const nodeDiv = document.createElement('div');
            nodeDiv.className = 'heap-node';
            nodeDiv.innerHTML = `
                <div class="heap-node-index">${i}</div>
                <div class="heap-node-score">${node.priority_score.toFixed(1)}</div>
                <div class="heap-node-zone" title="${node.zone_name}">${node.zone_name.split(' (')[0]}</div>
                <div class="heap-node-res">${node.resource_type.split(' ')[0]}</div>
            `;
            levelDiv.appendChild(nodeDiv);
        }
        container.appendChild(levelDiv);
    }

    visualizer.appendChild(container);
}

// ==========================================================================
// 5. Action Handlers (Form, Allocation, Simulation)
// ==========================================================================
function setupEventListeners() {
    // Reset DB Action
    document.getElementById('btn-reset-db').addEventListener('click', () => {
        if (confirm("Are you sure you want to reset the database back to default inventory and clean queues?")) {
            fetch('/api/reset', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        simulationResults = null;
                        loadDashboardData();
                        alert("Database reset successfully.");
                    }
                });
        }
    });

    // Custom Request Submission
    document.getElementById('request-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const zoneId = document.getElementById('req-zone').value;
        const resourceType = document.getElementById('req-resource').value;
        const qty = document.getElementById('req-qty').value;

        fetch('/api/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ zone_id: zoneId, resource_type: resourceType, quantity: qty })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('request-form').reset();
                loadDashboardData();
                alert(`Emergency Request registered successfully! priority score: ${data.priority_score}`);
            } else {
                alert("Error registering request: " + data.message);
            }
        });
    });

    // Live Resource Allocation execution
    document.getElementById('btn-run-allocation').addEventListener('click', () => {
        fetch('/api/allocate', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    loadDashboardData();
                    if (data.allocations.length > 0) {
                        let msg = "Allocations Complete!\n\n";
                        data.allocations.forEach(a => {
                            msg += `${a.zone_name}: Allocated ${a.allocated_quantity}/${a.requested_quantity} units of ${a.resource_type} (Status: ${a.status})\n`;
                        });
                        alert(msg);
                    } else {
                        alert("No requests to allocate.");
                    }
                }
            });
    });

    // Run Simulation Scenario
    document.getElementById('btn-run-sim').addEventListener('click', () => {
        const scenario = document.getElementById('scenario-select').value;
        if (!scenario) {
            alert("Please select a live crisis scenario first!");
            return;
        }

        activeScenario = scenario;
        const runBtn = document.getElementById('btn-run-sim');
        runBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
        runBtn.disabled = true;

        fetch(`/api/simulate/${scenario}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Sim';
                runBtn.disabled = false;

                if (data.status === 'success') {
                    simulationResults = data.results;
                    
                    // Render Metrics Comparison
                    renderSimulationMetrics(data.results);
                    
                    // Render Knapsack results
                    renderKnapsackOverview(data.results.proposed.dispatches);
                    
                    // Render Branch & Bound assignment logs
                    renderBranchBoundLog(data.results.proposed.dispatches);

                    // Switch to Simulation Analytics Tab
                    document.querySelector('[data-tab="tab-simulation"]').click();
                    
                    // Load and highlight the first valid path on the map
                    loadMapSimulationPaths(data.results.proposed.dispatches);
                    
                    // Reload base database levels
                    loadDashboardData();
                } else {
                    alert("Simulation run failed: " + data.message);
                }
            })
            .catch(err => {
                runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Sim';
                runBtn.disabled = false;
                alert("Simulation error: " + err);
            });
    });
}

// ==========================================================================
// 6. Simulation UI updates
// ==========================================================================
function renderSimulationMetrics(results) {
    document.getElementById('sim-scenario-desc').innerHTML = `
        Active Scenario: <b style="color:var(--primary); font-family:var(--font-heading);">${results.scenario}</b> - ${results.description}
    `;

    // Traditional Stats
    const trad = results.traditional;
    document.getElementById('m-trad-time').innerText = trad.avg_response_time_min > 0 ? `${trad.avg_response_time_min} m` : '-';
    document.getElementById('m-trad-dist').innerText = `${trad.total_distance_km} km`;
    document.getElementById('m-trad-util').innerText = `${trad.resource_utilization_pct}%`;
    document.getElementById('m-trad-success').innerText = `${trad.success_rate_pct}%`;

    // Proposed Stats
    const prop = results.proposed;
    document.getElementById('m-prop-time').innerText = prop.avg_response_time_min > 0 ? `${prop.avg_response_time_min} m` : '-';
    document.getElementById('m-prop-dist').innerText = `${prop.total_distance_km} km`;
    document.getElementById('m-prop-util').innerText = `${prop.resource_utilization_pct}%`;
    document.getElementById('m-prop-success').innerText = `${prop.success_rate_pct}%`;

    // Update global stat displays on main tab
    document.getElementById('stat-avg-resp-time').innerText = `${prop.avg_response_time_min} min`;

    // Update charts.js charts
    updateCharts(trad, prop);
}

function renderKnapsackOverview(dispatches) {
    const container = document.getElementById('cargo-knapsack-overview');
    container.innerHTML = '';

    const validDispatches = dispatches.filter(d => d.assigned_zone !== 'Idle');
    if (validDispatches.length === 0) {
        container.innerHTML = `
            <div class="empty-state-small">
                <i class="fa-solid fa-box-open"></i>
                <p>No active dispatches. Run a scenario first.</p>
            </div>
        `;
        return;
    }

    validDispatches.forEach(d => {
        const itemBox = document.createElement('div');
        itemBox.className = 'card glass-card';
        itemBox.style.marginBottom = '16px';
        itemBox.style.padding = '12px';

        const vehicle = appData.vehicles.find(v => v.vehicle_id === d.vehicle_id);
        const maxCapacity = vehicle ? vehicle.capacity_weight : 400;

        let loadRows = '';
        let loadedWeight = 0;
        let loadedValue = 0;

        // Calculate total loaded value first to determine percentage contribution
        let totalValForPct = 0;
        Object.entries(d.loaded_resources).forEach(([name, qty]) => {
            const res = appData.resources.find(r => r.resource_name === name);
            const val = res ? res.utility_value : 0;
            totalValForPct += val * qty;
        });

        Object.entries(d.loaded_resources).forEach(([name, qty]) => {
            const res = appData.resources.find(r => r.resource_name === name);
            const wt = res ? res.unit_weight : 0;
            const val = res ? res.utility_value : 0;
            const totalW = wt * qty;
            const totalV = val * qty;
            loadedWeight += totalW;
            loadedValue += totalV;

            const valPct = totalValForPct > 0 ? ((totalV / totalValForPct) * 100).toFixed(1) : '0.0';

            loadRows += `
                <div class="knapsack-item-bar">
                    <span>${name} (x${qty})</span>
                    <span class="badge badge-success">${totalW.toFixed(1)} kg | +${totalV} pts (${valPct}%)</span>
                </div>
            `;
        });

        let leftRows = '';
        Object.entries(d.left_behind_resources).forEach(([name, qty]) => {
            const res = appData.resources.find(r => r.resource_name === name);
            const wt = res ? res.unit_weight : 0;
            const val = res ? res.utility_value : 0;
            const totalW = wt * qty;
            const totalV = val * qty;

            leftRows += `
                <div class="knapsack-item-bar" style="border-color:rgba(255, 23, 68, 0.15)">
                    <span>${name} (x${qty})</span>
                    <span class="badge badge-danger">${totalW.toFixed(1)} kg | -${totalV} pts</span>
                </div>
            `;
        });

        const shortZoneName = d.assigned_zone.split(' (')[0];

        itemBox.innerHTML = `
            <div style="font-weight:700; margin-bottom:10px; font-size:12px; color:var(--primary);">
                ${d.vehicle_name} &rarr; ${shortZoneName}
            </div>
            <div style="font-size:11px; margin-bottom:10px; color:var(--text-secondary); line-height: 1.4;">
                Route Distance: <b>${d.distance_km.toFixed(1)} km</b> | Travel Time: <b>${d.travel_time_min.toFixed(1)} mins</b>
            </div>
            <div>
                <p style="font-size:10px; font-weight:600; margin-bottom:4px; text-transform:uppercase;">Cargo Load (${loadedWeight.toFixed(1)} / ${maxCapacity} kg):</p>
                ${loadRows || '<p style="font-size:11px; color:var(--text-muted); margin:0;">No cargo loaded.</p>'}
                ${leftRows ? '<p style="font-size:10px; font-weight:600; margin:10px 0 4px 0; text-transform:uppercase;">Capacities Exceeded (Left Behind):</p>' + leftRows : ''}
            </div>
            <div class="knapsack-rationale" style="margin-top:12px; padding-top:10px; border-top:1px dashed var(--border-glass); font-size:11px; color:var(--text-secondary); line-height: 1.4;">
                <div style="font-weight:600; text-transform:uppercase; margin-bottom:6px; color:var(--warning); font-size:10px;">
                    <i class="fa-solid fa-calculator"></i> Knapsack Optimization Rationale
                </div>
                <div style="margin-bottom:4px;">
                    Hold Load Utilized: <b>${Math.round((loadedWeight / maxCapacity) * 100)}%</b>
                </div>
                <div style="margin-bottom:6px;">
                    Total Delivered Utility: <b style="color:var(--success);">${loadedValue} points</b>
                </div>
                <p style="font-size:10px; line-height:1.4; color:var(--text-muted); margin:0;">
                    <b>Algorithm Decision:</b> The 0/1 Knapsack DP solver prioritized items with the highest utility density (e.g. Medicine at 50 pts/kg, Food at 40 pts/kg) and left behind heavier, less efficient items (like Rescue Gear at 6 pts/kg) once the capacity of ${maxCapacity} kg was reached.
                </p>
            </div>
        `;
        container.appendChild(itemBox);
    });
}

function renderBranchBoundLog(dispatches) {
    const container = document.getElementById('bb-decision-logic');
    container.innerHTML = '';

    const validDispatches = dispatches.filter(d => d.assigned_zone !== 'Idle');
    if (validDispatches.length === 0) {
        container.innerHTML = `
            <div class="empty-state-small">
                <i class="fa-solid fa-code-fork"></i>
                <p>No active assignments. Run a scenario first.</p>
            </div>
        `;
        return;
    }

    const logBox = document.createElement('div');
    logBox.style.fontSize = '12px';
    logBox.style.lineHeight = '1.6';

    let logHtml = `
        <p style="margin-bottom:8px;"><b>Optimization Solved:</b></p>
        <ul style="padding-left:16px; margin-bottom:12px; color:var(--text-secondary);">
    `;
    
    validDispatches.forEach(d => {
        logHtml += `
            <li>
                Assigned <b>${d.vehicle_name}</b> to <b>${d.assigned_zone}</b>:<br>
                Travel Cost: $${d.travel_cost} | Risk Penalty: $${d.risk_penalty} | Left-behind Utility Penalty: $${d.capacity_penalty}
            </li>
        `;
    });
    logHtml += '</ul>';

    logHtml += `
        <div class="badge badge-info" style="width:100%; justify-content:center; padding:8px;">
            Total BB Optimization Cost: $${dispatches.reduce((acc, curr) => acc + curr.total_cost, 0).toFixed(2)}
        </div>
    `;

    logBox.innerHTML = logHtml;
    container.appendChild(logBox);
}

// Map interactions & routing links
function loadMapSimulationPaths(dispatches) {
    const mapTab = document.querySelector('[data-tab="tab-map"]');
    // Save dispatch list to window so that click functions inside map marker popups can invoke Dijkstra paths
    window.activeDispatches = dispatches;
}

window.inspectDijkstraRoute = function(zoneName) {
    const detailsContainer = document.getElementById('route-inspector-details');
    detailsContainer.innerHTML = `
        <div class="empty-state-small">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>Computing optimal route...</p>
        </div>
    `;

    // Find if there is an active dispatch for this zone in current simulation results
    let dispatch = null;
    if (window.activeDispatches) {
        dispatch = window.activeDispatches.find(d => d.assigned_zone === zoneName);
    }

    if (dispatch) {
        // If active dispatch exists, render immediately
        renderRouteDetails(dispatch, zoneName);
    } else {
        // No active dispatch (e.g., Anaheim in a flood scenario). Fetch ad-hoc route from backend.
        const scenario = document.getElementById('scenario-select').value || '';
        
        fetch(`/api/route_to?destination=${encodeURIComponent(zoneName)}&scenario=${scenario}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success' && data.path && data.path.length > 0) {
                    highlightRoute(data.path, appData.roads);

                    let risksHtml = '';
                    data.risks.forEach(r => {
                        let color = '#00e676';
                        if (r === 'Blocked') color = '#ff1744';
                        else if (r === 'Enemy-Controlled') color = '#ff9100';
                        else if (r === 'Flooded') color = '#2979ff';
                        else if (r === 'Damaged') color = '#ffd600';
                        
                        risksHtml += `<span class="badge" style="background-color:${color}22; color:${color}; margin-right:4px;">${r}</span>`;
                    });

                    // Estimate time using default average speed (65 km/h)
                    const estTime = roundVal((data.distance_km / 65) * 60);

                    detailsContainer.innerHTML = `
                        <div style="font-family:'Outfit'; font-size:15px; font-weight:700; margin-bottom:8px; color:var(--primary);">
                            Depot &rarr; ${zoneName}
                        </div>
                        <div style="font-size:11px; color:var(--warning); margin-bottom:12px; font-weight:600;">
                            <i class="fa-solid fa-triangle-exclamation"></i> Ad-Hoc Route (No Active Dispatch)
                        </div>
                        <div class="inspector-path">
                            ${data.path.map(n => `<span class="inspector-node">${n.split(' (')[0]}</span>`).join('')}
                        </div>
                        <div style="margin-top:12px;">
                            <div class="path-data-row"><span>Distance:</span> <span>${data.distance_km} km</span></div>
                            <div class="path-data-row"><span>Est. Travel Time:</span> <span>${estTime} mins (Avg Speed)</span></div>
                            <div class="path-data-row"><span>Route Status Risks:</span> <span>${risksHtml || 'Clear'}</span></div>
                        </div>
                    `;
                } else {
                    detailsContainer.innerHTML = `
                        <div class="empty-state-small">
                            <i class="fa-solid fa-circle-xmark"></i>
                            <p>No viable route found to <b>${zoneName}</b>. The zone may be completely isolated by blockages.</p>
                        </div>
                    `;
                }
            })
            .catch(err => {
                detailsContainer.innerHTML = `
                    <div class="empty-state-small">
                        <i class="fa-solid fa-circle-xmark"></i>
                        <p>Error calculating route: ${err}</p>
                    </div>
                `;
            });
    }
};

function renderRouteDetails(dispatch, zoneName) {
    highlightRoute(dispatch.path, appData.roads);

    let risksHtml = '';
    dispatch.risks.forEach(r => {
        let color = '#00e676';
        if (r === 'Blocked') color = '#ff1744';
        else if (r === 'Enemy-Controlled') color = '#ff9100';
        else if (r === 'Flooded') color = '#2979ff';
        else if (r === 'Damaged') color = '#ffd600';
        
        risksHtml += `<span class="badge" style="background-color:${color}22; color:${color}; margin-right:4px;">${r}</span>`;
    });

    const detailsContainer = document.getElementById('route-inspector-details');
    detailsContainer.innerHTML = `
        <div style="font-family:'Outfit'; font-size:15px; font-weight:700; margin-bottom:8px; color:var(--primary);">
            Depot &rarr; ${zoneName}
        </div>
        <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
            Assigned Vehicle: <b>${dispatch.vehicle_name}</b> (${dispatch.vehicle_type})
        </div>
        <div class="inspector-path">
            ${dispatch.path.map(n => `<span class="inspector-node">${n.split(' (')[0]}</span>`).join('')}
        </div>
        <div style="margin-top:12px;">
            <div class="path-data-row"><span>Distance:</span> <span>${dispatch.distance_km} km</span></div>
            <div class="path-data-row"><span>Est. Travel Time:</span> <span>${dispatch.travel_time_min} mins</span></div>
            <div class="path-data-row"><span>Route Status Risks:</span> <span>${risksHtml || 'Clear'}</span></div>
        </div>
    `;
}

// Error popups
function showErrorNotification(msg) {
    console.error(msg);
}
