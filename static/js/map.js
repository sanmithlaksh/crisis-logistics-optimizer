let mapInstance = null;
let markersGroup = null;
let roadsGroup = null;
let activeRouteLayer = null;

const defaultDepotCoords = [34.0522, -118.2437]; // fallback

const riskColors = {
    'Normal': '#00e676',          // Neon Green
    'Damaged': '#ffd600',         // Yellow
    'Flooded': '#2979ff',         // Blue
    'Enemy-Controlled': '#ff9100', // Orange
    'Blocked': '#ff1744'          // Red
};

function initMap() {
    if (mapInstance) return;

    mapInstance = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView(defaultDepotCoords, 11);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(mapInstance);

    L.control.zoom({
        position: 'bottomright'
    }).addTo(mapInstance);

    markersGroup = L.layerGroup().addTo(mapInstance);
    roadsGroup = L.layerGroup().addTo(mapInstance);
}

function updateMapData(zones, roads, activeRequests) {
    if (!mapInstance) initMap();

    markersGroup.clearLayers();
    roadsGroup.clearLayers();
    clearActiveRoute();

    const coordMap = {};

    // 1. Draw Zones and Depots
    zones.forEach(zone => {
        const coords = [zone.latitude, zone.longitude];
        coordMap[zone.name] = coords;

        // Custom styling for Depots vs Zones
        if (zone.is_depot) {
            const depotIcon = L.divIcon({
                className: 'custom-depot-marker',
                html: '<div style="background-color:#00f2fe; width:16px; height:16px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 10px #00f2fe;"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });
            const marker = L.marker(coords, { icon: depotIcon }).addTo(markersGroup);
            marker.bindPopup(`<b>${zone.name}</b><br><span style="color:#00f2fe; font-size:10px; font-weight:700;">SUPPLY HUB</span>`);
            return;
        }

        // Active request check
        const hasActiveRequest = activeRequests.some(r => r.zone_name === zone.name && r.status === 'Pending');
        
        let severityClass = 'severity-low';
        let markerColor = '#00e676';
        if (zone.severity === 'Critical') {
            severityClass = 'severity-critical';
            markerColor = '#ff1744';
        } else if (zone.severity === 'High') {
            severityClass = 'severity-high';
            markerColor = '#ff9100';
        } else if (zone.severity === 'Medium') {
            severityClass = 'severity-medium';
            markerColor = '#ffd600';
        }

        // Check if zone is active/deactivated
        const isDeactivated = zone.is_active === 0 || zone.is_active === false;
        if (isDeactivated) {
            markerColor = '#64748b'; // Grayed out
            severityClass = 'severity-deactivated';
        }

        let pulseHtml = '';
        if (hasActiveRequest && !isDeactivated) {
            pulseHtml = `<div class="pulsing-marker" style="border-color:${markerColor}; background-color:${markerColor}44; width:24px; height:24px; border-radius:50%; position:absolute; left:-4px; top:-4px;"></div>`;
        }

        const zoneHtml = `
            <div style="position:relative; width:16px; height:16px;">
                ${pulseHtml}
                <div style="background-color:${markerColor}; width:16px; height:16px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 8px ${markerColor}; position:absolute; z-index:5; ${isDeactivated ? 'opacity:0.6;' : ''}"></div>
                ${isDeactivated ? '<div style="position:absolute; color:#fff; font-size:10px; font-weight:bold; left:4px; top:-2px; z-index:10;">&times;</div>' : ''}
            </div>
        `;

        const zoneIcon = L.divIcon({
            className: 'custom-zone-marker',
            html: zoneHtml,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        const marker = L.marker(coords, { icon: zoneIcon }).addTo(markersGroup);
        
        const statusButton = isDeactivated 
            ? `<button onclick="setZoneActiveStatus(${zone.id}, true)" style="margin-top:8px; padding:4px 8px; font-size:10px; background:#00e676; border:none; border-radius:4px; font-weight:bold; color:#0b0f19; cursor:pointer; width:100%;">Reactivate Zone</button>`
            : `<button onclick="setZoneActiveStatus(${zone.id}, false)" style="margin-top:8px; padding:4px 8px; font-size:10px; background:#ff1744; border:none; border-radius:4px; font-weight:bold; color:#fff; cursor:pointer; width:100%;">Deactivate Zone</button>`;

        const popupContent = `
            <div style="color:#0f172a; font-family:'Inter', sans-serif;">
                <h4 style="margin:0 0 4px 0; font-family:'Outfit'; font-size:14px;">${zone.name}</h4>
                <p style="margin:2px 0; font-size:11px;"><b>Population:</b> ${zone.population.toLocaleString()}</p>
                <p style="margin:2px 0; font-size:11px;"><b>Severity:</b> <span class="${severityClass}">${isDeactivated ? 'DEACTIVATED' : zone.severity}</span></p>
                ${!isDeactivated ? `<button onclick="inspectDijkstraRoute('${zone.name}')" style="margin-top:8px; padding:4px 8px; font-size:10px; background:#00f2fe; border:none; border-radius:4px; font-weight:bold; color:#0b0f19; cursor:pointer; width:100%;">Inspect Route</button>` : ''}
                ${statusButton}
            </div>
        `;
        marker.bindPopup(popupContent);
    });

    // 2. Draw Road Polylines with Click Hazard Toggle
    roads.forEach(road => {
        const p1 = coordMap[road.source];
        const p2 = coordMap[road.destination];

        if (p1 && p2) {
            const color = riskColors[road.risk_level] || '#00e676';
            const weight = road.risk_level === 'Normal' ? 3 : 5;
            const dashArray = road.risk_level === 'Blocked' ? '6, 6' : 
                              road.risk_level === 'Damaged' ? '3, 6' : null;

            const polyline = L.polyline([p1, p2], {
                color: color,
                weight: weight,
                opacity: 0.65,
                dashArray: dashArray
            }).addTo(roadsGroup);

            polyline.bindPopup(`
                <div style="color:#0f172a; font-size:11px; font-family:'Inter', sans-serif;">
                    <b>Road:</b> ${road.source} &harr; ${road.destination}<br>
                    <b>Distance:</b> ${road.distance_km} km<br>
                    <b>Status:</b> <span style="font-weight:bold; color:${color};">${road.risk_level}</span><br>
                    <span style="font-size:9px; color:#64748b; display:block; margin-top:4px;">(Click road directly to cycle hazard level)</span>
                </div>
            `);

            // Interactive hazard level cycler
            polyline.on('click', () => {
                const hazardLevels = ['Normal', 'Damaged', 'Flooded', 'Enemy-Controlled', 'Blocked'];
                let nextIdx = (hazardLevels.indexOf(road.risk_level) + 1) % hazardLevels.length;
                let nextHazard = hazardLevels[nextIdx];

                fetch('/api/road/hazard', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: road.source,
                        destination: road.destination,
                        risk_level: nextHazard
                    })
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

function highlightRoute(pathNodes, roads) {
    clearActiveRoute();
    if (!pathNodes || pathNodes.length < 2) return;

    // Fetch coordinates mapping
    const coordMap = {};
    zones.forEach(zone => {
        coordMap[zone.name] = [zone.latitude, zone.longitude];
    });

    const routeCoords = [];
    pathNodes.forEach(node => {
        const coords = coordMap[node];
        if (coords) routeCoords.push(coords);
    });

    if (routeCoords.length < 2) return;

    activeRouteLayer = L.featureGroup().addTo(mapInstance);
    const tempPoly = L.polyline(routeCoords);
    mapInstance.fitBounds(tempPoly.getBounds(), { padding: [60, 60] });

    let currentSegmentIndex = 0;
    
    function drawNextSegment() {
        if (currentSegmentIndex >= routeCoords.length - 1) {
            activeRouteLayer.clearLayers();

            // Glow path outer
            L.polyline(routeCoords, {
                color: '#00f2fe',
                weight: 10,
                opacity: 0.15,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'route-glow-line'
            }).addTo(activeRouteLayer);

            // Flow dash core
            L.polyline(routeCoords, {
                color: '#00f2fe',
                weight: 5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'animated-route-path'
            }).addTo(activeRouteLayer);

            // Solid inner
            L.polyline(routeCoords, {
                color: '#ffffff',
                weight: 2,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'route-core-line'
            }).addTo(activeRouteLayer);

            return;
        }

        const p1 = routeCoords[currentSegmentIndex];
        const p2 = routeCoords[currentSegmentIndex + 1];

        L.polyline([p1, p2], {
            color: '#00f2fe',
            weight: 6,
            opacity: 0.9,
            className: 'route-drawing-segment'
        }).addTo(activeRouteLayer);

        currentSegmentIndex++;
        setTimeout(drawNextSegment, 150);
    }

    drawNextSegment();
}

function drawRouteComparison(oldPath, newPath) {
    clearActiveRoute();
    if (!mapInstance) initMap();
    
    activeRouteLayer = L.featureGroup().addTo(mapInstance);
    
    const coordMap = {};
    zones.forEach(zone => {
        coordMap[zone.name] = [zone.latitude, zone.longitude];
    });

    const getCoords = (path) => {
        const coords = [];
        path.forEach(n => {
            const c = coordMap[n];
            if (c) coords.push(c);
        });
        return coords;
    };

    const oldCoords = getCoords(oldPath);
    const newCoords = getCoords(newPath);

    if (oldCoords.length >= 2) {
        L.polyline(oldCoords, {
            color: '#ff1744',
            weight: 4,
            dashArray: '6, 8',
            opacity: 0.8,
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(activeRouteLayer).bindPopup("<b>Original Route: Blocked / Failed</b>");
    }

    if (newCoords.length >= 2) {
        L.polyline(newCoords, {
            color: '#00e676',
            weight: 10,
            opacity: 0.15,
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(activeRouteLayer);

        L.polyline(newCoords, {
            color: '#00e676',
            weight: 5,
            opacity: 0.85,
            lineCap: 'round',
            lineJoin: 'round',
            className: 'animated-route-path'
        }).addTo(activeRouteLayer).bindPopup("<b>Alternate Detour Route: Safe</b>");

        const tempPoly = L.polyline(newCoords);
        mapInstance.fitBounds(tempPoly.getBounds(), { padding: [60, 60] });
    }
}

function clearActiveRoute() {
    if (activeRouteLayer && mapInstance) {
        mapInstance.removeLayer(activeRouteLayer);
        activeRouteLayer = null;
    }
}
