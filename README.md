# Turnov Třídí – Svoz odpadu 🗑️

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/davidlouda/turnov-tridi-hacs)](https://github.com/davidlouda/turnov-tridi-hacs/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom Home Assistant integrace pro zobrazení termínů svozu odpadu ve městě **Turnov**. Data se načítají ze stránky [turnovtridi.cz](http://turnovtridi.cz/kdy-kde-svazime-odpad).

## Funkce

- 📅 Zobrazuje **nejbližší termíny svozu** pro každý typ odpadu
- 🏠 Konfigurace **ulice** přes GUI (Nastavení → Zařízení a služby)
- 🔄 Automatická aktualizace dat každých **6 hodin**
- 📊 Senzory s atributy pro snadnou automatizaci

### Podporované typy odpadu

| Senzor | Typ odpadu | Ikona |
|--------|-----------|-------|
| Směsný komunální odpad | SKO | 🗑️ |
| Plasty | Plast | ♻️ |
| Papír | Papír | 📰 |
| Bio odpad | Bio | 🌿 |
| Nejbližší svoz | Další svoz libovolného typu | 📅 |

## Instalace

### HACS (doporučeno)

1. Otevřete **HACS** v Home Assistantu
2. Klikněte na **⋮** (tři tečky) → **Vlastní repozitáře**
3. Vložte URL: `https://github.com/davidlouda/turnov-tridi-hacs`
4. Kategorie: **Integrace**
5. Klikněte **Přidat** a poté nainstalujte integraci
6. **Restartujte** Home Assistant

### Ruční instalace

1. Stáhněte složku `custom_components/turnov_tridi` z tohoto repozitáře
2. Zkopírujte ji do `<config>/custom_components/turnov_tridi`
3. Restartujte Home Assistant

## Konfigurace

1. Přejděte do **Nastavení** → **Zařízení a služby**
2. Klikněte **+ Přidat integraci**
3. Vyhledejte **Turnov Třídí**
4. Zadejte **název ulice** (např. `Károvsko`, `Bezručova`, `5. května`)
5. Klikněte **Odeslat**

Integrace ověří, že pro danou ulici existují data, a vytvoří senzory.

## Senzory a atributy

Každý senzor typu odpadu poskytuje:

| Atribut | Popis |
|---------|-------|
| `state` | Datum příštího svozu (formát YYYY-MM-DD) |
| `street` | Název ulice |
| `waste_type` | Typ odpadu |
| `days_until` | Počet dnů do příštího svozu |
| `is_today` | `true` pokud je svoz dnes |
| `is_tomorrow` | `true` pokud je svoz zítra |
| `upcoming_dates` | Seznam příštích 5 termínů |

Senzor **Nejbližší svoz** navíc obsahuje:

| Atribut | Popis |
|---------|-------|
| `waste_type` | Typ odpadu nejbližšího svozu |
| `upcoming_summary` | Přehled nejbližších svozů všech typů |

## Příklady automatizací

### Oznámení den před svozem

V UI přejděte na **Nastavení → Automatizace → + Vytvořit automatizaci → ⋮ → Upravit v YAML** a vložte:

```yaml
alias: "Upozornění na svoz odpadu"
trigger:
  - platform: state
    entity_id: sensor.svoz_odpadu_karovsko_nejblizsi_svoz
condition:
  - condition: template
    value_template: "{{ state_attr('sensor.svoz_odpadu_karovsko_nejblizsi_svoz', 'is_tomorrow') }}"
action:
  - service: notify.mobile_app
    data:
      title: "🗑️ Svoz odpadu zítra!"
      message: >
        Zítra se vyváží: {{ state_attr('sensor.svoz_odpadu_karovsko_nejblizsi_svoz', 'waste_type') }}
```

### Zobrazení v Lovelace kartě (základní)

```yaml
type: entities
title: Svoz odpadu
entities:
  - entity: sensor.svoz_odpadu_karovsko_nejblizsi_svoz
  - entity: sensor.svoz_odpadu_karovsko_smesny_komunalni_odpad
  - entity: sensor.svoz_odpadu_karovsko_plasty
  - entity: sensor.svoz_odpadu_karovsko_papir
  - entity: sensor.svoz_odpadu_karovsko_bio_odpad
```

## Custom Lovelace karta 🎨

Součástí integrace je **graficky bohatá Lovelace karta** s:

- 🎯 Barevně odlišenými typy odpadu (šedá = SKO, žlutá = plasty, modrá = papír, zelená = bio)
- 📍 Zvýrazněním nejbližšího svozu (obrys + pulsní animace pro dnešní svoz)
- 📅 Časovou osou nadcházejících svozů s barevnými čipy
- 🏷️ Odznaky „DNES", „ZÍTRA", „za X dní"
- 🌙 Plnou podporou tmavého režimu
- ⚙️ Vizuálním editorem konfigurace přímo v Lovelace

### Přidání Lovelace karty

1. Po instalaci integrace se karta automaticky zkopíruje do `www/community/turnov_tridi/`
2. Přidejte zdroj v **Nastavení → Dashboardy → ⋮ → Zdroje**:
   - URL: `/local/community/turnov_tridi/turnov-tridi-card.js`
   - Typ: **JavaScript modul**
3. Na dashboard přidejte **Ruční kartu** s konfigurací:

```yaml
type: custom:turnov-tridi-card
entity: sensor.svoz_odpadu_karovsko_nejblizsi_svoz
title: Svoz odpadu
show_header: true
show_timeline: true
```

### Možnosti konfigurace karty

| Parametr | Výchozí | Popis |
|----------|---------|-------|
| `entity` | *povinný* | Entity ID senzoru „Nejbližší svoz" |
| `title` | `Svoz odpadu` | Titulek karty |
| `show_header` | `true` | Zobrazit hlavičku s dalším svozem |
| `show_timeline` | `true` | Zobrazit časovou osu |
| `show_days_badge` | `true` | Zobrazit odznaky dní |
| `compact` | `false` | Kompaktní režim (menší řádky) |

### Vzhled karty

Karta automaticky zobrazí:

- **Hlavička** — další nadcházející svoz s barevnou ikonou, typem odpadu a datem
- **4 řádky odpadu** — každý typ s barevným proužkem, ikonou, datem a odpočtem dní; nejbližší svoz má zvýrazněný rámeček, dnešní svoz pulsuje
- **Časová osa** — chronologický přehled všech nadcházejících svozů seskupených po dnech s barevnými čipy

## Zdroj dat

Data pocházejí z [turnovtridi.cz](http://turnovtridi.cz/kdy-kde-svazime-odpad) — projekt Města Turnov.

## Licence

[MIT](LICENSE)
