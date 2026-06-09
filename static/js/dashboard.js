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

            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            tabPages.forEach(p => p.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');

            const config = tabConfig[targetTab];
            if (config) {
                document.getElementById('current-tab-title').innerText = config.title;
                document.getElementById('current-tab-desc').innerText = config.desc;
            }

            if (targetTab === 'tab-map') {
                setTimeout(() => {
                    initMap();
                    if (mapInstance) {
                        mapInstance.invalidateSize();
                        updateMapData(appData.zones, appData.roads, appData.requests);
                        renderZoneToggles();
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
                updateLiveMetrics();
                
                if (mapInstance && document.getElementById('tab-map').classList.contains('active')) {
                    updateMapData(appData.zones, appData.roads, appData.requests);
                    renderZoneToggles();
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
function renderInventory() {
    const container = document.getElementById('inventory-list');
    const tableBody = document.getElementById('resource-weights-table');
    if (!container || !tableBody) return;
    container.innerHTML = '';
    tableBody.innerHTML = '';

    const icons = {
        'Medicine': '<i class="fa-solid fa-kit-medical"></i>',
        'Food Packets': '<i class="fa-solid fa-box-tissue"></i>',
        'Water Crate': '<i class="fa-solid fa-bottle-water"></i>',
        'Fuel Ltrs': '<i class="fa-solid fa-gas-pump"></i>',
        'Rescue Gear': '<i class="fa-solid fa-helmet-safety"></i>',
        'Emergency Personnel': '<i class="fa-solid fa-user-doctor"></i>'
    };

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

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><b>${res.resource_name}</b></td>
            <td>${res.unit_weight} kg</td>
            <td><span class="badge badge-info">${res.utility_value} pts</span></td>
        `;
        tableBody.appendChild(row);
    });
}

function renderRequests() {
    const tableBody = document.getElementById('requests-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '';

    const pendingRequests = appData.requests.filter(r => r.status === 'Pending');
    document.getElementById('stat-active-requests').innerText = pendingRequests.length;

    if (appData.requests.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No active requests. Select a scenario or submit a manual request.</td></tr>`;
        renderHeap([]);
        return;
    }

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

        // Gray out if zone is deactivated
        const isDeactivated = req.is_active === 0 || req.is_active === false;
        if (isDeactivated) {
            statusBadge = '<span class="badge" style="background:#475569; color:#fff;">Offline Zone</span>';
        }

        const row = document.createElement('tr');
        row.style.opacity = isDeactivated ? 0.45 : 1.0;
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

    const heapItems = pendingRequests
        .filter(r => r.is_active !== 0 && r.is_active !== false)
        .map(r => ({
            zone_name: r.zone_name,
            resource_type: r.resource_type,
            priority_score: r.priority
        }));
    
    buildMaxHeap(heapItems);
    renderHeap(heapItems);
}

function renderFleet() {
    const container = document.getElementById('fleet-list');
    if (!container) return;
    container.innerHTML = '';

    appData.vehicles.forEach(vehicle => {
        const card = document.createElement('div');
        card.className = 'fleet-card';
        
        let statusClass = 'available';
        if (vehicle.status === 'Dispatched') statusClass = 'dispatched';
        
        let assignmentText = '<div class="fleet-assignment-box idle">Idle</div>';
        if (simulationResults && simulationResults.proposed && simulationResults.proposed.dispatches) {
            const assignment = simulationResults.proposed.dispatches.find(d => d.vehicle_id === vehicle.vehicle_id);
            if (assignment && assignment.assigned_zone !== 'Idle') {
                assignmentText = `<div class="fleet-assignment-box">Dispatched from <b>${assignment.optimal_depot || 'Depot'}</b> to <b>${assignment.assigned_zone}</b></div>`;
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
    if (!select) return;
    select.innerHTML = '<option value="" disabled selected>Select affected zone</option>';
    
    // Only show active zones that are not depots
    appData.zones.filter(z => z.is_active && !z.is_depot).forEach(zone => {
        const opt = document.createElement('option');
        opt.value = zone.id;
        opt.innerText = `${zone.name} (${zone.severity})`;
        select.appendChild(opt);
    });
}

function renderZoneToggles() {
    const container = document.getElementById('zone-toggles-list');
    if (!container) return;
    container.innerHTML = '';

    const zones = appData.zones.filter(z => !z.is_depot);
    zones.forEach(zone => {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.justifyContent = 'space-between';
        row.style.alignItems = 'center';
        row.style.marginBottom = '6px';
        row.style.fontSize = '11px';

        const nameSpan = document.createElement('span');
        nameSpan.innerText = zone.name.split(' (')[0];
        nameSpan.style.color = zone.is_active ? 'var(--text-primary)' : 'var(--text-muted)';
        if (!zone.is_active) nameSpan.style.textDecoration = 'line-through';

        const toggleBtn = document.createElement('button');
        toggleBtn.innerText = zone.is_active ? 'Active' : 'Offline';
        toggleBtn.style.padding = '2px 6px';
        toggleBtn.style.fontSize = '9px';
        toggleBtn.style.borderRadius = '4px';
        toggleBtn.style.border = 'none';
        toggleBtn.style.cursor = 'pointer';
        toggleBtn.style.fontWeight = 'bold';
        toggleBtn.style.width = '55px';
        toggleBtn.style.textAlign = 'center';
        toggleBtn.style.color = '#0b0f19';
        toggleBtn.style.background = zone.is_active ? '#00e676' : '#64748b';

        toggleBtn.addEventListener('click', () => {
            window.setZoneActiveStatus(zone.id, !zone.is_active);
        });

        row.appendChild(nameSpan);
        row.appendChild(toggleBtn);
        container.appendChild(row);
    });
}

window.setZoneActiveStatus = function(zoneId, isActive) {
    fetch('/api/zone/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: zoneId, is_active: isActive })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            let count = parseInt(document.getElementById('metric-recalculations').innerText) || 0;
            document.getElementById('metric-recalculations').innerText = count + 1;
            loadDashboardData();
        }
    });
};

function updateLiveMetrics() {
    // 1. Active Zones
    const activeZones = appData.zones.filter(z => z.is_active && !z.is_depot).length;
    document.getElementById('metric-active-zones').innerText = activeZones;
    document.getElementById('stat-total-zones').innerText = activeZones;

    // 2. Total Requests
    document.getElementById('metric-total-requests').innerText = appData.requests.length;

    // 3. Delivered Resource Units
    const delivered = appData.requests
        .filter(r => r.status === 'Allocated' || r.status === 'Partial')
        .reduce((sum, r) => sum + r.quantity, 0);
    document.getElementById('metric-delivered-qty').innerText = delivered;

    // 4. Hazard Roads
    const hazardRoads = appData.roads.filter(r => r.risk_level !== 'Normal').length;
    document.getElementById('metric-blocked-roads').innerText = hazardRoads;
}

// ==========================================================================
// 4. Binary Heap Tree Drawer
// ==========================================================================
function buildMaxHeap(arr) {
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
    if (!visualizer) return;
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

    const totalLevels = Math.ceil(Math.log2(heapArray.length + 1));

    for (let l = 0; l < Math.min(totalLevels, 4); l++) {
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
// 5. Action Handlers (Form, Toggles, Simulation, Failures)
// ==========================================================================
function setupEventListeners() {
    // Reset Database
    document.getElementById('btn-reset-db').addEventListener('click', () => {
        if (confirm("Reset database to standard inventory and clean queues?")) {
            fetch('/api/reset', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        simulationResults = null;
                        document.getElementById('metric-recalculations').innerText = '0';
                        document.getElementById('metric-heap-ops').innerText = '0';
                        document.getElementById('metric-dijkstra-runs').innerText = '0';
                        document.getElementById('metric-bb-nodes').innerText = '0';
                        loadDashboardData();
                        alert("Database reset successfully.");
                    }
                });
        }
    });

    // Custom Request Form Submission
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
                alert(`Request added. priority score: ${data.priority_score}`);
            } else {
                alert("Error registering request: " + data.message);
            }
        });
    });

    // Greedy Allocation Rerun
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
            alert("Select a crisis scenario first.");
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
                    renderSimulationMetrics(data.results);
                    renderKnapsackOverview(data.results.proposed.dispatches);
                    renderBranchBoundLog(data.results.proposed.dispatches);
                    document.querySelector('[data-tab="tab-simulation"]').click();
                    loadMapSimulationPaths(data.results.proposed.dispatches);
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

    // UPGRADE 2: Large Scale Disaster Generation
    document.getElementById('btn-add-zones').addEventListener('click', () => {
        const btn = document.getElementById('btn-add-zones');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scaling...';
        btn.disabled = true;

        fetch('/api/simulate/large', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                btn.innerHTML = '<i class="fa-solid fa-circle-plus"></i> +10 Zones';
                btn.disabled = false;

                if (data.status === 'success') {
                    simulationResults = data.results;
                    renderSimulationMetrics(data.results);
                    renderKnapsackOverview(data.results.proposed.dispatches);
                    renderBranchBoundLog(data.results.proposed.dispatches);
                    loadDashboardData();
                    alert(data.message + " Scaling simulation ran successfully.");
                } else {
                    alert("Failed to scale zones: " + data.message);
                }
            });
    });

    // UPGRADE 4: Supply Shortage
    document.getElementById('btn-shortage').addEventListener('click', () => {
        fetch('/api/simulate/shortage', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    loadDashboardData();
                    alert("Resource shortage activated. Warehouse stock reduced to 10%. Allocation recalculations completed.");
                }
            });
    });

    // UPGRADE 6: Disaster Spread BFS
    document.getElementById('btn-spread').addEventListener('click', () => {
        fetch('/api/simulate/spread', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    loadDashboardData();
                    if (data.spread_zones.length > 0) {
                        let msg = `Disaster propagated to adjacent zones via BFS:\n\n`;
                        data.spread_zones.forEach(z => {
                            msg += `- ${z.name}: Upgraded to ${z.severity} severity.\n`;
                        });
                        alert(msg);
                    } else {
                        alert("Disaster spread completed. No new neighboring zones affected.");
                    }
                } else {
                    alert("Spread error: " + data.message);
                }
            });
    });

    // UPGRADE 7: Route Failure Detour
    document.getElementById('btn-route-failure').addEventListener('click', () => {
        fetch('/api/simulate/route_failure', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    loadDashboardData();
                    
                    // Direct map comparison draw
                    document.querySelector('[data-tab="tab-map"]').click();
                    setTimeout(() => {
                        window.drawRouteComparison(
                            ['Depot A (Central)', 'Zone A (Glendale)', 'Zone B (Pasadena)'],
                            ['Depot A (Central)', 'Zone C (East LA)', 'Zone B (Pasadena)']
                        );
                        
                        const detailsContainer = document.getElementById('route-inspector-details');
                        detailsContainer.innerHTML = `
                            <div style="font-family:'Outfit'; font-size:15px; font-weight:700; margin-bottom:8px; color:var(--primary);">
                                Route Failure Detour (Depot A &rarr; Pasadena)
                            </div>
                            <div style="font-size:11px; color:#ff1744; margin-bottom:8px; font-weight:600;">
                                <i class="fa-solid fa-triangle-exclamation"></i> Road Collapse Mid-Transit!
                            </div>
                            <div style="font-size:11px; margin-bottom:12px; color:var(--text-secondary); line-height: 1.4;">
                                <b>Original Path (Red):</b> Depot A &rarr; Glendale &rarr; Pasadena (19.7 km)<br>
                                <b>Detour Path (Green):</b> Depot A &rarr; East LA &rarr; Pasadena (22.7 km)
                            </div>
                            <div class="inspector-path" style="margin-top:6px;">
                                <span class="inspector-node" style="border-color:#ff1744; background:rgba(255,23,68,0.1); color:#ff1744;">Depot A</span>
                                <span class="inspector-node" style="border-color:#ff1744; background:rgba(255,23,68,0.1); color:#ff1744;">Glendale</span>
                                <span class="inspector-node" style="border-color:#00e676; background:rgba(0,230,118,0.1); color:#00e676;">East LA</span>
                                <span class="inspector-node" style="border-color:#00e676; background:rgba(0,230,118,0.1); color:#00e676;">Pasadena</span>
                            </div>
                        `;
                    }, 300);
                    
                    alert("Transit road collapse simulated! Glendale <-> Pasadena blocked. Detour calculated on map.");
                }
            });
    });

    // Manual Recalculation
    document.getElementById('btn-recalculate').addEventListener('click', () => {
        let count = parseInt(document.getElementById('metric-recalculations').innerText) || 0;
        document.getElementById('metric-recalculations').innerText = count + 1;
        loadDashboardData();
        alert("Forced route and allocation recalculations complete.");
    });

    // Random Zone Deactivation
    document.getElementById('btn-random-deactivate').addEventListener('click', () => {
        fetch('/api/zone/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ random: true })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.message);
                let count = parseInt(document.getElementById('metric-recalculations').innerText) || 0;
                document.getElementById('metric-recalculations').innerText = count + 1;
                loadDashboardData();
            } else {
                alert(data.message);
            }
        });
    });

    // Legend Preset buttons
    ['damaged', 'flooded', 'enemy', 'blocked'].forEach(cat => {
        const btn = document.getElementById(`toggle-${cat}-preset`);
        if (btn) {
            btn.addEventListener('click', () => {
                const catMap = {
                    'damaged': 'Damaged',
                    'flooded': 'Flooded',
                    'enemy': 'Enemy-Controlled',
                    'blocked': 'Blocked'
                };
                fetch('/api/road/hazard', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: catMap[cat] })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        loadDashboardData();
                    }
                });
            });
        }
    });
}

// ==========================================================================
// 6. Simulation UI updates
// ==========================================================================
function renderSimulationMetrics(results) {
    document.getElementById('sim-scenario-desc').innerHTML = `
        Active Scenario: <b style="color:var(--primary); font-family:var(--font-heading);">${results.scenario}</b> - ${results.description}
    `;

    // Update Ribbon stats from simulation execution data
    if (results.stats) {
        document.getElementById('metric-heap-ops').innerText = results.stats.heap_ops;
        document.getElementById('metric-dijkstra-runs').innerText = results.stats.dijkstra_ops;
        document.getElementById('metric-bb-nodes').innerText = results.stats.bb_nodes;
        document.getElementById('metric-avg-response').innerText = `${results.proposed.avg_response_time_min} m`;
    }

    const trad = results.traditional;
    document.getElementById('m-trad-time').innerText = trad.avg_response_time_min > 0 ? `${trad.avg_response_time_min} m` : '-';
    document.getElementById('m-trad-dist').innerText = `${trad.total_distance_km} km`;
    document.getElementById('m-trad-util').innerText = `${trad.resource_utilization_pct}%`;
    document.getElementById('m-trad-success').innerText = `${trad.success_rate_pct}%`;

    const prop = results.proposed;
    document.getElementById('m-prop-time').innerText = prop.avg_response_time_min > 0 ? `${prop.avg_response_time_min} m` : '-';
    document.getElementById('m-prop-dist').innerText = `${prop.total_distance_km} km`;
    document.getElementById('m-prop-util').innerText = `${prop.resource_utilization_pct}%`;
    document.getElementById('m-prop-success').innerText = `${prop.success_rate_pct}%`;

    document.getElementById('stat-avg-resp-time').innerText = `${prop.avg_response_time_min} min`;

    // Dynamic advantage statements in Algorithm breakdown table
    const timeAdv = trad.avg_response_time_min - prop.avg_response_time_min;
    if (timeAdv > 0) {
        document.getElementById('adv-priority').innerText = `Critical dispatches processed ${timeAdv.toFixed(1)} mins faster`;
        document.getElementById('adv-priority').style.color = '#00e676';
    }
    const distSaved = trad.total_distance_km - prop.total_distance_km;
    if (distSaved > 0) {
        document.getElementById('adv-dispatch').innerText = `Fleet delivery costs minimized by saving ${distSaved.toFixed(1)} km`;
        document.getElementById('adv-dispatch').style.color = '#00e676';
    }
    const utilAdv = prop.resource_utilization_pct - trad.resource_utilization_pct;
    if (utilAdv > 0) {
        document.getElementById('adv-cargo').innerText = `Cargo utility density increased by +${utilAdv.toFixed(1)}%`;
        document.getElementById('adv-cargo').style.color = '#00e676';
    }
    const successAdv = prop.success_rate_pct - trad.success_rate_pct;
    if (successAdv > 0) {
        document.getElementById('adv-routing').innerText = `Safe path success rate increased by +${successAdv.toFixed(1)}%`;
        document.getElementById('adv-routing').style.color = '#00e676';
    }

    updateCharts(trad, prop);
}

function renderKnapsackOverview(dispatches) {
    const container = document.getElementById('cargo-knapsack-overview');
    if (!container) return;
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

        let demandsHtml = '';
        const originalRequests = {};
        Object.entries(d.loaded_resources).forEach(([name, qty]) => {
            originalRequests[name] = (originalRequests[name] || 0) + qty;
        });
        Object.entries(d.left_behind_resources).forEach(([name, qty]) => {
            originalRequests[name] = (originalRequests[name] || 0) + qty;
        });
        Object.entries(originalRequests).forEach(([name, qty]) => {
            demandsHtml += `<span class="badge" style="background: rgba(255, 255, 255, 0.05); color: var(--text-secondary); margin-right: 4px; margin-bottom: 4px; display: inline-block; padding: 4px 6px;">${name}: ${qty}</span>`;
        });

        itemBox.innerHTML = `
            <div style="font-weight:700; margin-bottom:10px; font-size:12px; color:var(--primary);">
                ${d.vehicle_name} &rarr; ${shortZoneName} (${d.optimal_depot || 'Hub'})
            </div>
            <div style="font-size:11px; margin-bottom:10px; color:var(--text-secondary); line-height: 1.4;">
                Route Distance: <b>${d.distance_km.toFixed(1)} km</b> | Travel Time: <b>${d.travel_time_min.toFixed(1)} mins</b>
            </div>
            <div style="margin-bottom: 12px; padding: 8px; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-glass); border-radius: 6px;">
                <div style="font-size: 10px; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; color: var(--text-primary);">Total Requested by Zone:</div>
                <div style="display: flex; flex-wrap: wrap;">${demandsHtml}</div>
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
    if (!container) return;
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
                Assigned <b>${d.vehicle_name}</b> to <b>${d.assigned_zone}</b> (starting from <b>${d.optimal_depot || 'Hub'}</b>):<br>
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

function loadMapSimulationPaths(dispatches) {
    window.activeDispatches = dispatches;
}

window.inspectDijkstraRoute = function(zoneName) {
    const detailsContainer = document.getElementById('route-inspector-details');
    if (!detailsContainer) return;
    detailsContainer.innerHTML = `
        <div class="empty-state-small">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>Computing optimal route...</p>
        </div>
    `;

    let dispatch = null;
    if (window.activeDispatches) {
        dispatch = window.activeDispatches.find(d => d.assigned_zone === zoneName);
    }

    if (dispatch) {
        renderRouteDetails(dispatch, zoneName);
    } else {
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

                    const estTime = roundVal((data.distance_km / 65) * 60);

                    detailsContainer.innerHTML = `
                        <div style="font-family:'Outfit'; font-size:15px; font-weight:700; margin-bottom:8px; color:var(--primary);">
                            ${data.optimal_depot || 'Hub'} &rarr; ${zoneName}
                        </div>
                        <div style="font-size:11px; color:var(--warning); margin-bottom:12px; font-weight:600;">
                            <i class="fa-solid fa-triangle-exclamation"></i> Ad-Hoc Route (No Active Dispatch)
                        </div>
                        <div class="inspector-path">
                            ${data.path.map(n => `<span class="inspector-node">${n.split(' (')[0]}</span>`).join('')}
                        </div>
                        <div style="margin-top:12px;">
                            <div class="path-data-row"><span>Source Depot:</span> <span>${data.optimal_depot || 'Hub'}</span></div>
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
            ${dispatch.optimal_depot || 'Hub'} &rarr; ${zoneName}
        </div>
        <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
            Assigned Vehicle: <b>${dispatch.vehicle_name}</b> (${dispatch.vehicle_type})
        </div>
        <div class="inspector-path">
            ${dispatch.path.map(n => `<span class="inspector-node">${n.split(' (')[0]}</span>`).join('')}
        </div>
        <div style="margin-top:12px;">
            <div class="path-data-row"><span>Source Depot:</span> <span>${dispatch.optimal_depot || 'Hub'}</span></div>
            <div class="path-data-row"><span>Distance:</span> <span>${dispatch.distance_km} km</span></div>
            <div class="path-data-row"><span>Est. Travel Time:</span> <span>${dispatch.travel_time_min} mins</span></div>
            <div class="path-data-row"><span>Route Status Risks:</span> <span>${risksHtml || 'Clear'}</span></div>
        </div>
    `;
}

function showErrorNotification(msg) {
    console.error(msg);
}

function roundVal(val) {
    return Math.round(val * 100) / 100;
}
