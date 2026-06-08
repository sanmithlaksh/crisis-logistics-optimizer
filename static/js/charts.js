let barChartInstance = null;
let radarChartInstance = null;

function initCharts() {
    const ctxBar = document.getElementById('chart-comparison-bar').getContext('2d');
    const ctxRadar = document.getElementById('chart-comparison-radar').getContext('2d');
    
    // Custom Chart.js globals/defaults for dark mode
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = 'Inter, sans-serif';
    Chart.defaults.font.size = 11;
    
    // 1. Bar Chart Initialization
    barChartInstance = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: ['Avg Response Time (min)', 'Total Distance (km)'],
            datasets: [
                {
                    label: 'Baseline (FCFS)',
                    data: [0, 0],
                    backgroundColor: 'rgba(255, 23, 68, 0.4)',
                    borderColor: '#ff1744',
                    borderWidth: 2,
                    borderRadius: 6
                },
                {
                    label: 'Proposed AI Engine',
                    data: [0, 0],
                    backgroundColor: 'rgba(0, 242, 254, 0.4)',
                    borderColor: '#00f2fe',
                    borderWidth: 2,
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 16
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                }
            }
        }
    });

    // 2. Radar Chart Initialization
    radarChartInstance = new Chart(ctxRadar, {
        type: 'radar',
        data: {
            labels: [
                'Resource Delivery %', 
                'Delivery Success %', 
                'Distance Efficiency %', 
                'Response Time Score %'
            ],
            datasets: [
                {
                    label: 'Baseline (FCFS)',
                    data: [0, 0, 0, 0],
                    backgroundColor: 'rgba(255, 23, 68, 0.15)',
                    borderColor: '#ff1744',
                    borderWidth: 2,
                    pointBackgroundColor: '#ff1744'
                },
                {
                    label: 'Proposed AI Engine',
                    data: [0, 0, 0, 0],
                    backgroundColor: 'rgba(0, 242, 254, 0.15)',
                    borderColor: '#00f2fe',
                    borderWidth: 2,
                    pointBackgroundColor: '#00f2fe'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 16
                    }
                }
            },
            scales: {
                r: {
                    angleLines: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    pointLabels: {
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        backdropColor: 'transparent',
                        color: '#64748b'
                    },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
}

function updateCharts(trad, prop) {
    if (!barChartInstance || !radarChartInstance) {
        initCharts();
    }

    // Update Bar Chart
    barChartInstance.data.datasets[0].data = [trad.avg_response_time_min, trad.total_distance_km];
    barChartInstance.data.datasets[1].data = [prop.avg_response_time_min, prop.total_distance_km];
    barChartInstance.update();

    // Update Radar Chart
    // Distance efficiency formula (compare against each other, higher is better):
    // If distance is 0, set to 100. Otherwise ratio of lower distance / current distance
    const minDistance = Math.min(trad.total_distance_km, prop.total_distance_km);
    const tradDistEff = trad.total_distance_km > 0 ? (minDistance / trad.total_distance_km) * 100 : 100;
    const propDistEff = prop.total_distance_km > 0 ? (minDistance / prop.total_distance_km) * 100 : 100;

    // Response time score: higher is better. Ratio of lower response time / current response time
    const minTime = Math.min(trad.avg_response_time_min, prop.avg_response_time_min);
    const tradTimeScore = trad.avg_response_time_min > 0 ? (minTime / trad.avg_response_time_min) * 100 : 100;
    const propTimeScore = prop.avg_response_time_min > 0 ? (minTime / prop.avg_response_time_min) * 100 : 100;

    radarChartInstance.data.datasets[0].data = [
        trad.resource_utilization_pct,
        trad.success_rate_pct,
        roundVal(tradDistEff),
        roundVal(tradTimeScore)
    ];

    radarChartInstance.data.datasets[1].data = [
        prop.resource_utilization_pct,
        prop.success_rate_pct,
        roundVal(propDistEff),
        roundVal(propTimeScore)
    ];
    radarChartInstance.update();
}

function roundVal(v) {
    return Math.round(v * 100) / 100;
}
