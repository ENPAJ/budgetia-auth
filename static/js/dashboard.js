document.addEventListener("DOMContentLoaded", function () {

  if (typeof window.dashboardData === "undefined") {
    console.warn("dashboardData not found");
    return;
  }

  const { pieLabels, pieData, lineLabels, lineData, addExpenseUrl } = window.dashboardData;

  // --------- Line Chart ----------
  const lineCanvas = document.getElementById('lineChart');
  if (lineCanvas) {
    new Chart(lineCanvas, {
      type: 'line',
      data: {
        labels: lineLabels,
        datasets: [{
          label: 'Dépenses',
          data: lineData,
          fill: false
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false }},
        scales: { y: { beginAtZero: true }}
      }
    });
  }

  // --------- Pie Chart ----------
  const pieCanvas = document.getElementById('pieChart');
  if (pieCanvas) {
    new Chart(pieCanvas, {
      type: 'pie',
      data: {
        labels: pieLabels,
        datasets: [{
          data: pieData,
          backgroundColor: pieLabels.map((_, i) => `hsl(${i * 45 % 360} 70% 55%)`)
        }]
      },
      options: {
        responsive: true
      }
    });
  }

  // --------- Formulaire ajout dépense ----------
  const expenseForm = document.getElementById('expenseForm');

  if (expenseForm) {
    expenseForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const data = new FormData(expenseForm);
      const res = await fetch(addExpenseUrl, {
        method: 'POST',
        body: data
      });

      const result = await res.json();
      const alertBox = document.getElementById('alertBox');

      alertBox.innerHTML = '';

      if (!result.ok) {
        alertBox.innerHTML = `<div class="alert alert-danger">Erreur</div>`;
        return;
      }

      if (result.warning) {
        const level = result.warning.level === 'danger'
          ? 'danger'
          : result.warning.level === 'warning'
          ? 'warning'
          : 'info';

        alertBox.innerHTML = `<div class="alert alert-${level}">
          ${result.warning.message}
        </div>`;
      } else {
        alertBox.innerHTML = `<div class="alert alert-success">
          Dépense ajoutée — ${result.pct_category}% du budget
        </div>`;
      }

      const remain = document.getElementById('remainGlobal');
      if (remain) {
        remain.innerText = result.remaining_global + "€";
      }

      setTimeout(() => location.reload(), 700);
    });
  }

});
