/* SkyProject Web UI */

// SSE log stream
function initLogStream() {
    const container = document.getElementById('log-container');
    if (!container) return;

    const source = new EventSource('/api/logs/stream');
    source.onmessage = function(event) {
        const line = document.createElement('div');
        line.className = 'log-line';
        const text = event.data;
        if (text.includes('ERROR')) line.classList.add('ERROR');
        else if (text.includes('WARNING')) line.classList.add('WARNING');
        else if (text.includes('INFO')) line.classList.add('INFO');
        else line.classList.add('DEBUG');
        line.textContent = text;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
    };
    source.onerror = function() {
        setTimeout(() => initLogStream(), 5000);
        source.close();
    };
}

// Task status pie chart
function initTaskChart(data) {
    const ctx = document.getElementById('taskChart');
    if (!ctx || !data) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: ['#6b7280', '#3b82f6', '#10b981', '#ef4444', '#f59e0b'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9ca3af', font: { size: 11 } }
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initLogStream();
});
