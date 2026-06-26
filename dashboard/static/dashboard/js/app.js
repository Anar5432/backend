// ── ORDER GRID SEARCH ──
function filterOrders(query) {
  const q = query.toLowerCase();
  const cards = document.querySelectorAll('.order-card');
  let visibleCount = 0;

  cards.forEach(card => {
    const searchData = card.getAttribute('data-search');
    if (searchData.includes(q)) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  const badge = document.getElementById('order-count');
  if (badge) badge.textContent = visibleCount;
}

// ── ORDER DETAIL SLIDE-IN ──
function loadOrderDetail(orderId) {
  // Highlight selected card
  document.querySelectorAll('.order-card').forEach(c => c.classList.remove('selected'));
  event.currentTarget.classList.add('selected');

  const panel = document.getElementById('detail-panel');
  panel.classList.add('open');

  // Load content via HTMX manually to place inside the panel
  panel.innerHTML = '<div class="detail-empty">Yüklənir...</div>';
  htmx.ajax('GET', '/htmx/order/' + orderId + '/', {target: '#detail-panel', swap: 'innerHTML'});
}

function closeOrderDetail() {
  document.getElementById('detail-panel').classList.remove('open');
  document.querySelectorAll('.order-card').forEach(c => c.classList.remove('selected'));
}

// ── CHARTS ──
let trendChartInstance = null;
let stockChartInstance = null;

async function initCharts() {
  try {
    // 1. Fetch Trend Data
    const trendRes = await fetch('/api/chart-data/');
    const trendData = await trendRes.json();

    const labels = trendData.production.map(d => d.month);
    const prodQty = trendData.production.map(d => d.qty_produced);

    // Group sales by category
    const salesMen = labels.map(m => {
      const found = trendData.sales.find(s => s.month === m && s.category === 'KİŞİ CORABI');
      return found ? found.qty_sold : 0;
    });
    const salesWomen = labels.map(m => {
      const found = trendData.sales.find(s => s.month === m && s.category === 'QADIN CORABI');
      return found ? found.qty_sold : 0;
    });
    const salesKids = labels.map(m => {
      const found = trendData.sales.find(s => s.month === m && s.category === 'UŞAQ CORABI');
      return found ? found.qty_sold : 0;
    });

    const ctxTrend = document.getElementById('trendChart');
    if (ctxTrend) {
      if (trendChartInstance) trendChartInstance.destroy();
      trendChartInstance = new Chart(ctxTrend, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'İstehsal (Cüt)',
              data: prodQty,
              type: 'line',
              borderColor: '#10b981',
              backgroundColor: '#10b981',
              borderWidth: 2,
              tension: 0.3,
              yAxisID: 'y'
            },
            {
              label: 'Satış: Kişi',
              data: salesMen,
              backgroundColor: '#3b82f6',
              stack: 'Stack 0',
              yAxisID: 'y'
            },
            {
              label: 'Satış: Qadın',
              data: salesWomen,
              backgroundColor: '#f472b6',
              stack: 'Stack 0',
              yAxisID: 'y'
            },
            {
              label: 'Satış: Uşaq',
              data: salesKids,
              backgroundColor: '#facc15',
              stack: 'Stack 0',
              yAxisID: 'y'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' } }
          },
          plugins: {
            legend: { labels: { color: '#94a3b8' } }
          }
        }
      });
    }

    // 2. Fetch Stock Data
    const stockRes = await fetch('/api/stock-data/');
    const stockJson = await stockRes.json();
    const stockLabels = stockJson.stock.map(s => s.warehouse);
    const stockData = stockJson.stock.map(s => s.total_qty);

    const ctxStock = document.getElementById('stockChart');
    if (ctxStock) {
      if (stockChartInstance) stockChartInstance.destroy();
      stockChartInstance = new Chart(ctxStock, {
        type: 'doughnut',
        data: {
          labels: stockLabels,
          datasets: [{
            data: stockData,
            backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { color: '#94a3b8' } }
          },
          cutout: '70%'
        }
      });
    }

  } catch (err) {
    console.error('Chart error:', err);
  }
}

// Initialize charts on first load, and re-init when HTMX swaps the chart section
document.addEventListener('DOMContentLoaded', initCharts);
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'charts-section') {
    initCharts();
  }
});
