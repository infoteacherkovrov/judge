document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('myChart').getContext('2d');
    const data = window.chartData; 
    let currentChart = null;

    function renderChart(chartData) {
        if (currentChart) {
            currentChart.destroy();
        }

        if (!chartData || chartData.length === 0) {
            document.getElementById('myChart').parentElement.innerHTML += 
                '<p style="text-align: center; color: #999; margin-top: 20px;">Нет данных за выбранный период</p>';
            return;
        }

        const labels = chartData.map(item => item.day);
        const uniqueCorrectData = chartData.map(item => item.unique_solved);
        const wrongAttemptsData = chartData.map(item => item.wrong_attempts);

        currentChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Принято (решено уникальных задач',
                        data: uniqueCorrectData,
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.3)',
                        tension: 0.4,
                        fill: true,
                        order: 1
                    },
                    {
                        label: 'Неверно (ошибочных попыток)',
                        data: wrongAttemptsData,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.05)',
                        tension: 0.4,
                        fill: true,
                        borderDash: [2, 5],
                        order: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: { title: { display: true, text: 'Дата' }, ticks: { maxRotation: 45, minRotation: 45 } },
                    y: { title: { display: true, text: 'Количество' }, beginAtZero: true, ticks: {precision: 0},stepSize: 1 }
                },
                plugins: { 
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.parsed.y;
                                if (context.dataset.label.includes('Уникальных')) {
                                    return `✅ Уникальных решено: ${val}`;
                                } else {
                                    return `❌ Ошибок (попыток): ${val}`;
                                }
                            }
                        }
                    }
                }
            }
        });
    }

    renderChart(data);
});
