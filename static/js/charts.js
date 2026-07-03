// Chart.js rendering for the trend + forecast chart.
let trendChart = null;

function fmtHour(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit' });
}

function renderTrend(history, forecast) {
  const ctx = document.getElementById('trendChart').getContext('2d');
  const histPts = history.points.map(p => ({ x: p.ts * 1000, y: p.value }));
  const fcPts = forecast.points.map(p => ({ x: p.ts * 1000, y: p.yhat }));
  const bandLow = forecast.points.map(p => ({ x: p.ts * 1000, y: p.low }));
  const bandHigh = forecast.points.map(p => ({ x: p.ts * 1000, y: p.high }));

  // Bridge the last history point into the forecast line for continuity.
  if (histPts.length && fcPts.length) {
    fcPts.unshift(histPts[histPts.length - 1]);
    bandLow.unshift(histPts[histPts.length - 1]);
    bandHigh.unshift(histPts[histPts.length - 1]);
  }

  const data = {
    datasets: [
      {
        label: history.label + ' (measured)', data: histPts,
        borderColor: '#22d3ee', backgroundColor: 'transparent',
        borderWidth: 2, pointRadius: 0, tension: 0.3,
      },
      {
        label: 'Forecast', data: fcPts,
        borderColor: '#4f8cff', borderDash: [6, 4],
        borderWidth: 2, pointRadius: 0, tension: 0.3,
      },
      {
        label: 'Confidence band', data: bandHigh,
        borderColor: 'transparent', backgroundColor: 'rgba(79,140,255,0.15)',
        pointRadius: 0, fill: '+1',
      },
      {
        label: '_low', data: bandLow,
        borderColor: 'transparent', backgroundColor: 'transparent', pointRadius: 0, fill: false,
      },
    ],
  };

  const options = {
    responsive: true, maintainAspectRatio: false,
    resizeDelay: 250,            // debounce resizes — extra guard against resize churn
    animation: false,            // no animation loop → chart cannot drive continuous frames
    events: ['mousemove', 'mouseout', 'click'],  // no scroll/resize-driven redraw churn
    interaction: { mode: 'index', intersect: false },
    scales: {
      x: { type: 'linear', ticks: { color: '#93a2c4', maxTicksLimit: 7, callback: v => fmtHour(v / 1000) },
           grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#93a2c4' }, grid: { color: 'rgba(255,255,255,0.05)' },
           title: { display: true, text: 'µg/m³', color: '#93a2c4' } },
    },
    plugins: {
      legend: { labels: { color: '#e8eefc', filter: i => !i.text.startsWith('_') && !i.text.startsWith('Confidence') } },
      tooltip: { callbacks: { title: items => fmtHour(items[0].parsed.x / 1000) } },
    },
  };

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, { type: 'line', data, options });
}
