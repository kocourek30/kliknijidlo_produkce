document.addEventListener('DOMContentLoaded', function() {
  const dateInput = document.querySelector('input[name="datum_objednavky"]');
  if (!dateInput) return;

  let container = document.createElement('div');
  container.id = 'jidelnicek-polozky-container';
  dateInput.parentElement.appendChild(container);

  dateInput.addEventListener('change', function() {
    const datum = this.value;
    if (!datum) {
      container.innerHTML = '';
      return;
    }

    fetch(`/admin/objednavky/objednavka/jidelnicek-items/?datum=${datum}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          container.innerHTML = `<p style="color:red">${data.error}</p>`;
          return;
        }
        let html = `<h4>Jídelníček: ${data.jidelnicek}</h4>`;
        data.polozky.forEach(polozka => {
          html += `
            <label>
              <input type="checkbox" name="jidlo_ids" value="${polozka.id}">
              <i class="${polozka.ikona}"></i> ${polozka.druh_jidla} - ${polozka.jidlo}
            </label><br>
          `;
        });
        container.innerHTML = html;
      });
  });
});
