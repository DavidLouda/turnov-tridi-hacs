# Changelog

## 1.1.0

Vyžaduje Home Assistant **2025.1** nebo novější.

### Nové funkce
- 🗓️ **Kalendář** `calendar.svoz_odpadu_<ulice>` se všemi svozy jako celodenními událostmi – lze použít v kalendáři HA i pro automatizace (viz README).
- 🎨 **Karta se načítá automaticky** – už není potřeba ručně přidávat zdroj do dashboardu.
- 🔁 **Změna ulice** přes *Překonfigurovat* bez mazání integrace.
- ♻️ Senzor **Nejbližší svoz** zobrazuje všechny typy odpadu vyvážené ve stejný den (`waste_type: "Plasty, Papír"`, nové atributy `waste_types` a `waste_keys`); karta je ukazuje v hlavičce.
- Senzory typů odpadu mají nový atribut `waste_key`.

### Opravy
- Stav senzorů a odpočet dní se přepočítají přesně o půlnoci (dříve až se zpožděním 6 hodin).
- Datum se počítá v časové zóně nastavené v Home Assistantu.
- Fungují anglické názvy entit (české instalace si zachovají stávající ID entit).
- Při dočasném výpadku webu turnovtridi.cz zůstane zobrazen poslední známý rozpis místo prázdných senzorů.
- Mezery kolem názvu ulice se už neukládají.
- Karta: opraveno chybné přiřazení senzoru „Nejbližší svoz“ místo senzoru konkrétního typu odpadu; hodnoty z konfigurace se escapují.

### Aktualizace z 1.0
Dřívější verze kopírovala kartu do `www/community/turnov_tridi/` a vyžadovala ruční zdroj `/local/community/turnov_tridi/turnov-tridi-card.js`. Integrace starou kopii smaže – zdroj odstraňte v **Nastavení → Dashboardy → ⋮ → Zdroje** a obnovte stránku prohlížeče.
