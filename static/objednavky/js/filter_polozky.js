document.addEventListener('DOMContentLoaded', function() {

  // Najdi input datum_vydeje
  const datumInput = document.querySelector('#id_datum_vydeje');
  if (!datumInput) {
    console.error('Datum výdeje input nebyl nalezen');
    return;
  }

  // Vytvoř nebo najdi blok pro položky jídelníčku pod polem datum
  let polozkyInlineContainer = document.querySelector('#polozky-inline-container');
  if (!polozkyInlineContainer) {
    polozkyInlineContainer = document.createElement('div');
    polozkyInlineContainer.id = 'polozky-inline-container';
    polozkyInlineContainer.style.border = '1px solid #ccc';
    polozkyInlineContainer.style.padding = '10px';
    polozkyInlineContainer.style.marginTop = '10px';
    polozkyInlineContainer.textContent = 'Vyber datum a položky jídelníčku se zde zobrazí.';
    // Vložíme blok přímo za řádek s polem datum_vydeje
    datumInput.parentElement.parentElement.insertAdjacentElement('afterend', polozkyInlineContainer);
  }

  const jidelnicekData = window.jidelnicek_data || [];

  function najdiJidelnicek(datum) {
    const d = new Date(datum);
    return jidelnicekData.find(j => new Date(j.platnost_od) <= d && new Date(j.platnost_do) >= d);
  }

  function vytvorPolozkuElement(polozka) {
    const btn = document.createElement('button');
    btn.textContent = `${polozka.jidlo_nazev} (${polozka.cena} Kč)`;
    btn.type = 'button';
    btn.style.margin = '3px';
    btn.addEventListener('click', () => {
      pridejPolozkuDoInline(polozka);
    });
    return btn;
  }

  function pridejPolozkuDoInline(polozka) {
    const totalForms = document.querySelector('#id_polozkyobjednavky_set-TOTAL_FORMS');
    if (!totalForms) {
      alert('Nepodařilo se najít počet formulářů inline položek.');
      return;
    }
    const currentFormCount = parseInt(totalForms.value, 10);
    const emptyForm = document.querySelector('.dynamic-polozkyobjednavky_set.empty-form');
    if (!emptyForm) {
      alert('Nepodařilo se najít prázdný formulář pro přidání položky.');
      return;
    }

    // Klonuj prázdný inline formulář a přizpůsob ho novému indexu
    const newForm = emptyForm.cloneNode(true);
    newForm.classList.remove('empty-form');
    newForm.style.display = '';

    // Nahraď __prefix__ aktuálním indexem
    const regex = new RegExp('__prefix__', 'g');
    newForm.innerHTML = newForm.innerHTML.replace(regex, currentFormCount);

    // Nastav hodnotu polí jidlo a cena
    const jidloSelect = newForm.querySelector('select[name$="-jidlo"]');
    const cenaInput = newForm.querySelector('input[name$="-cena"]');

    if (jidloSelect) {
      jidloSelect.value = polozka.jidlo_id;
    }
    if (cenaInput) {
      cenaInput.value = polozka.cena;
    }

    // Přidej nový formulář do kontejneru
    const container = document.querySelector('.polozkyobjednavky_set-group');
    if (container) {
      container.appendChild(newForm);
      // Zvyšte počet formulářů
      totalForms.value = currentFormCount + 1;
    } else {
      alert('Nepodařilo se najít kontejner pro inline položky.');
    }
  }

  function zobrazPolozky(jidelnicek) {
    if (!polozkyInlineContainer) return;

    polozkyInlineContainer.innerHTML = '';

    if (!jidelnicek || !jidelnicek.polozky.length) {
      polozkyInlineContainer.textContent = 'Pro vybrané datum není dostupný jídelníček.';
      return;
    }

    jidelnicek.polozky.forEach(polozka => {
      const btn = vytvorPolozkuElement(polozka);
      polozkyInlineContainer.appendChild(btn);
    });
  }

  // Přidáme event listener na změnu data
  datumInput.addEventListener('change', () => {
    const vybraneDatum = datumInput.value;
    const jidelnicek = najdiJidelnicek(vybraneDatum);
    zobrazPolozky(jidelnicek);
  });

});
