let mapInstance = null;
let markersGroup = null;
let roadsGroup = null;
let activeRouteLayer = null;

const depotCoords = [34.0522, -118.2437]; // LA City Hall

// Color scheme for road risk levels
const riskColors = {
    'Normal': '#00e676',          // Neon Green
    'Damaged': '#ffd600',         // Yellow
    'Flooded': '#2979ff',         // Blue
    'Enemy-Controlled': '#ff9100', // Orange
    'Blocked': '#ff1744'          // Red
};

function initMap() {
    if (mapInstance) return;

    // Center map around LA Depot
    mapInstance = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView(depotCoords, 11);

    // CartoDB Dark Matter tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(mapInstance);

    // Add zoom control at bottom-right
    L.control.zoom({
        position: 'bottomright'
    }).addTo(mapInstance);

    markersGroup = L.layerGroup().addTo(mapInstance);
    roadsGroup = L.layerGroup().addTo(mapInstance);

    // Plot depot marker
    const depotIcon = L.divIcon({
        className: 'custom-depot-marker',
        html: '<div style="background-color:#00f2fe; width:16px; height:16px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 10px #00f2fe;"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });
    L.marker(depotCoords, { icon: depotIcon }).addTo(mapInstance).bindPopup("<b>Central Supply Depot</b>");
}

function updateMapData(zones, roads, activeRequests) {
    if (!mapInstance) initMap();

    markersGroup.clearLayers();
    roadsGroup.clearLayers();
    clearActiveRoute();

    // Map zone name to coordinates for easy road rendering
    const coordMap = {
        'Depot': depotCoords
    };

    // Draw Zone Markers
    zones.forEach(zone => {
        const coords = [zone.latitude, zone.longitude];
        coordMap[zone.name] = coords;

        // Check if there are active requests for this zone
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

        let pulseHtml = '';
        if (hasActiveRequest) {
            pulseHtml = `<div class="pulsing-marker" style="border-color:${markerColor}; background-color:${markerColor}44; width:24px; height:24px; border-radius:50%; position:absolute; left:-4px; top:-4px;"></div>`;
        }

        const zoneIcon = L.divIcon({
            className: 'custom-zone-marker',
            html: `
                <div style="position:relative; width:16px; height:16px;">
                    ${pulseHtml}
                    <div style="background-color:${markerColor}; width:16px; height:16px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 8px ${markerColor}; position:absolute; z-index:5;"></div>
                </div>
            `,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        const marker = L.marker(coords, { icon: zoneIcon }).addTo(markersGroup);
        
        const popupContent = `
            <div style="color:#0f172a; font-family:'Inter', sans-serif;">
                <h4 style="margin:0 0 4px 0; font-family:'Outfit'; font-size:14px;">${zone.name}</h4>
                <p style="margin:2px 0; font-size:11px;"><b>Population:</b> ${zone.population.toLocaleString()}</p>
                <p style="margin:2px 0; font-size:11px;"><b>Severity:</b> <span class="${severityClass}">${zone.severity}</span></p>
                <button onclick="inspectDijkstraRoute('${zone.name}')" style="margin-top:8px; padding:4px 8px; font-size:10px; background:#00f2fe; border:none; border-radius:4px; font-weight:bold; color:#0b0f19; cursor:pointer; width:100%;">Inspect Route</button>
            </div>
        `;
        marker.bindPopup(popupContent);
    });

    // Draw Road Polylines
    roads.forEach(road => {
        const p1 = coordMap[road.source];
        const p2 = coordMap[road.destination];

        if (p1 && p2) {
            const color = riskColors[road.risk_level] || '#00e676';
            const weight = road.risk_level === 'Normal' ? 3 : 4;
            const dashArray = road.risk_level === 'Blocked' ? '6, 6' : 
                              road.risk_level === 'Damaged' ? '3, 6' : null;

            L.polyline([p1, p2], {
                color: color,
                weight: weight,
                opacity: 0.65,
                dashArray: dashArray
            }).addTo(roadsGroup).bindPopup(`
                <div style="color:#0f172a; font-size:11px;">
                    <b>Road:</b> ${road.source} &harr; ${road.destination}<br>
                    <b>Distance:</b> ${road.distance_km} km<br>
                    <b>Status:</b> <span style="font-weight:bold; color:${color};">${road.risk_level}</span>
                </div>
            `);
        }
    });
}

function highlightRoute(pathNodes, roads) {
    clearActiveRoute();
    if (!pathNodes || pathNodes.length < 2) return;

    // Fetch coordinates for all nodes from current map markers
    const coordMap = { 'Depot': depotCoords };
    markersGroup.eachLayer(layer => {
        if (layer.getPopup()) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = layer.getPopup().getContent();
            const h4 = tempDiv.querySelector('h4');
            if (h4) {
                coordMap[h4.innerText] = [layer.getLatLng().lat, layer.getLatLng().lng];
            }
        }
    });

    const routeCoords = [];
    for (let i = 0; i < pathNodes.length; i++) {
        const coords = coordMap[pathNodes[i]];
        if (coords) {
            routeCoords.push(coords);
        }
    }

    if (routeCoords.length < 2) return;

    // Create a feature group to hold all active route segments
    activeRouteLayer = L.featureGroup().addTo(mapInstance);

    // Zoom to fit the route bounds first
    const tempPoly = L.polyline(routeCoords);
    mapInstance.fitBounds(tempPoly.getBounds(), { padding: [60, 60] });

    // Step-by-step drawing animation
    let currentSegmentIndex = 0;
    
    function drawNextSegment() {
        if (currentSegmentIndex >= routeCoords.length - 1) {
            // Once all segments are drawn, replace with the final highly-styled neon/glow flowing path
            activeRouteLayer.clearLayers();

            // 1. Thick Outer Glow Line
            L.polyline(routeCoords, {
                color: '#00f2fe',
                weight: 10,
                opacity: 0.15,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'route-glow-line'
            }).addTo(activeRouteLayer);

            // 2. Flowing Dash Line (Ant-path simulation via CSS)
            L.polyline(routeCoords, {
                color: '#00f2fe',
                weight: 5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'animated-route-path'
            }).addTo(activeRouteLayer);

            // 3. Ultra-Bright Solid Core Line
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

        // Draw active exploration segment
        L.polyline([p1, p2], {
            color: '#00f2fe',
            weight: 6,
            opacity: 0.9,
            className: 'route-drawing-segment'
        }).addTo(activeRouteLayer);

        currentSegmentIndex++;
        setTimeout(drawNextSegment, 200); // 200ms per edge transition
    }

    drawNextSegment();
}

function clearActiveRoute() {
    if (activeRouteLayer && mapInstance) {
        mapInstance.removeLayer(activeRouteLayer);
        activeRouteLayer = null;
    }
}
