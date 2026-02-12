/**
 * Turnov Třídí – Lovelace Card
 * Custom card for displaying waste collection schedules in Turnov.
 * 
 * Version: 1.0.0
 */

const WASTE_CONFIG = {
  mixed_waste: {
    label: 'Směsný odpad',
    icon: 'mdi:trash-can',
    color: '#6B7280',
    gradient: 'linear-gradient(135deg, #6B7280, #4B5563)',
    bgLight: '#F3F4F6',
    bgDark: '#374151',
  },
  plastic: {
    label: 'Plasty',
    icon: 'mdi:recycle',
    color: '#F59E0B',
    gradient: 'linear-gradient(135deg, #F59E0B, #D97706)',
    bgLight: '#FFFBEB',
    bgDark: '#78350F',
  },
  paper: {
    label: 'Papír',
    icon: 'mdi:newspaper-variant-outline',
    color: '#3B82F6',
    gradient: 'linear-gradient(135deg, #3B82F6, #2563EB)',
    bgLight: '#EFF6FF',
    bgDark: '#1E3A5F',
  },
  bio_waste: {
    label: 'Bio odpad',
    icon: 'mdi:leaf',
    color: '#10B981',
    gradient: 'linear-gradient(135deg, #10B981, #059669)',
    bgLight: '#ECFDF5',
    bgDark: '#064E3B',
  },
};

const DAYS_CS = ['Neděle', 'Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota'];
const MONTHS_CS = [
  'ledna', 'února', 'března', 'dubna', 'května', 'června',
  'července', 'srpna', 'září', 'října', 'listopadu', 'prosince',
];

class TurnovTridiCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
  }

  static getConfigElement() {
    return document.createElement('turnov-tridi-card-editor');
  }

  static getStubConfig() {
    return {
      title: 'Svoz odpadu',
      show_header: true,
      show_timeline: true,
    };
  }

  setConfig(config) {
    if (!config.entity && !config.street) {
      throw new Error('Zadejte "entity" (senzor nejbližšího svozu) nebo "street" v konfiguraci karty.');
    }
    this._config = {
      title: config.title || 'Svoz odpadu',
      show_header: config.show_header !== false,
      show_timeline: config.show_timeline !== false,
      show_days_badge: config.show_days_badge !== false,
      compact: config.compact || false,
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getEntities() {
    if (!this._hass) return {};

    const entities = {};
    const allEntityIds = Object.keys(this._hass.states);

    // Try to find entities by explicit config or auto-discover
    if (this._config.entities) {
      for (const [key, entityId] of Object.entries(this._config.entities)) {
        if (this._hass.states[entityId]) {
          entities[key] = this._hass.states[entityId];
        }
      }
    } else {
      // Auto-discover based on entity_id or street
      const search = this._config.entity
        ? this._config.entity.replace(/^sensor\./, '').replace(/_nejblizsi_svoz$|_next_collection$/, '')
        : null;

      for (const entityId of allEntityIds) {
        if (!entityId.startsWith('sensor.')) continue;

        const state = this._hass.states[entityId];
        const attrs = state.attributes || {};

        // Match by street attribute or entity ID pattern
        const matchByStreet = this._config.street &&
          attrs.street && attrs.street.toLowerCase() === this._config.street.toLowerCase();
        const matchByEntity = search && entityId.includes(search);

        if (matchByStreet || matchByEntity) {
          if (entityId.includes('smesny') || entityId.includes('mixed_waste') || attrs.waste_type === 'Směsný komunální odpad') {
            entities.mixed_waste = state;
          } else if (entityId.includes('plast') || entityId.includes('plastic') || attrs.waste_type === 'Plasty') {
            entities.plastic = state;
          } else if (entityId.includes('papir') || entityId.includes('paper') || attrs.waste_type === 'Papír') {
            entities.paper = state;
          } else if (entityId.includes('bio') || entityId.includes('bio_waste') || attrs.waste_type === 'Bio odpad') {
            entities.bio_waste = state;
          } else if (entityId.includes('nejblizsi') || entityId.includes('next_collection')) {
            entities.next_collection = state;
          }
        }
      }
    }

    return entities;
  }

  _formatDate(dateStr) {
    if (!dateStr || dateStr === 'unknown' || dateStr === 'unavailable') return null;
    const d = new Date(dateStr + 'T00:00:00');
    if (isNaN(d.getTime())) return null;
    return d;
  }

  _formatDateHuman(date) {
    if (!date) return '—';
    const day = DAYS_CS[date.getDay()];
    return `${day} ${date.getDate()}. ${MONTHS_CS[date.getMonth()]}`;
  }

  _getDaysUntil(date) {
    if (!date) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(date);
    target.setHours(0, 0, 0, 0);
    return Math.round((target - today) / (1000 * 60 * 60 * 24));
  }

  _getDaysBadge(days) {
    if (days === null || days === undefined) return { text: '—', class: 'badge-neutral' };
    if (days === 0) return { text: 'DNES', class: 'badge-today' };
    if (days === 1) return { text: 'ZÍTRA', class: 'badge-tomorrow' };
    if (days < 0) return { text: 'Proběhl', class: 'badge-neutral' };
    return { text: `za ${days} dn${days === 1 ? 'í' : days < 5 ? 'y' : 'í'}`, class: 'badge-future' };
  }

  _render() {
    const entities = this._getEntities();
    const wasteItems = [];

    for (const [key, cfg] of Object.entries(WASTE_CONFIG)) {
      const entity = entities[key];
      const date = entity ? this._formatDate(entity.state) : null;
      const days = this._getDaysUntil(date);

      wasteItems.push({
        key,
        ...cfg,
        date,
        dateHuman: this._formatDateHuman(date),
        days,
        badge: this._getDaysBadge(days),
        entityId: entity ? entity.entity_id : null,
      });
    }

    // Sort by date (nearest first), null dates last
    wasteItems.sort((a, b) => {
      if (!a.date && !b.date) return 0;
      if (!a.date) return 1;
      if (!b.date) return -1;
      return a.date - b.date;
    });

    // Find the very next collection
    const nextItem = wasteItems.find(i => i.days !== null && i.days >= 0) || null;

    // Build timeline items (all future collections across types, merged and sorted)
    const timelineItems = [];
    if (this._config.show_timeline) {
      for (const item of wasteItems) {
        const entity = entities[item.key];
        if (!entity) continue;
        const attrs = entity.attributes || {};
        const upcoming = attrs.upcoming_dates || [];
        for (const ds of upcoming.slice(0, 3)) {
          const d = this._formatDate(ds);
          if (d) {
            timelineItems.push({
              date: d,
              dateHuman: this._formatDateHuman(d),
              days: this._getDaysUntil(d),
              ...WASTE_CONFIG[item.key],
              key: item.key,
            });
          }
        }
      }
      timelineItems.sort((a, b) => a.date - b.date);
    }

    this.shadowRoot.innerHTML = `
      <style>${this._getStyles()}</style>
      <ha-card>
        ${this._config.show_header ? this._renderHeader(nextItem) : ''}
        <div class="card-content ${this._config.compact ? 'compact' : ''}">
          <div class="waste-grid">
            ${wasteItems.map(item => this._renderWasteItem(item, item === nextItem)).join('')}
          </div>
          ${this._config.show_timeline && timelineItems.length > 0 ? this._renderTimeline(timelineItems) : ''}
        </div>
      </ha-card>
    `;

    // Add click event handlers for entity more-info
    this.shadowRoot.querySelectorAll('[data-entity-id]').forEach(el => {
      el.addEventListener('click', () => {
        const entityId = el.getAttribute('data-entity-id');
        if (entityId && this._hass) {
          const event = new Event('hass-more-info', { bubbles: true, composed: true });
          event.detail = { entityId };
          this.dispatchEvent(event);
        }
      });
    });
  }

  _renderHeader(nextItem) {
    if (!nextItem || nextItem.days === null) {
      return `
        <div class="card-header">
          <div class="header-content">
            <div class="header-icon">
              <ha-icon icon="mdi:delete-empty-outline"></ha-icon>
            </div>
            <div class="header-text">
              <div class="header-title">${this._config.title}</div>
              <div class="header-subtitle">Žádný plánovaný svoz</div>
            </div>
          </div>
        </div>
      `;
    }

    const badge = nextItem.badge;
    return `
      <div class="card-header" style="--accent-color: ${nextItem.color}; --accent-gradient: ${nextItem.gradient}">
        <div class="header-content">
          <div class="header-icon" style="background: ${nextItem.gradient}">
            <ha-icon icon="${nextItem.icon}"></ha-icon>
          </div>
          <div class="header-text">
            <div class="header-title">${this._config.title}</div>
            <div class="header-subtitle">
              Další svoz: <strong>${nextItem.label}</strong> · ${nextItem.dateHuman}
            </div>
          </div>
          <div class="header-badge ${badge.class}">${badge.text}</div>
        </div>
      </div>
    `;
  }

  _renderWasteItem(item, isNext) {
    return `
      <div class="waste-item ${isNext ? 'is-next' : ''} ${item.days === 0 ? 'is-today' : ''}"
           style="--item-color: ${item.color}; --item-gradient: ${item.gradient}; --item-bg-light: ${item.bgLight}; --item-bg-dark: ${item.bgDark}"
           ${item.entityId ? `data-entity-id="${item.entityId}"` : ''}>
        <div class="waste-item-indicator"></div>
        <div class="waste-item-icon">
          <ha-icon icon="${item.icon}"></ha-icon>
        </div>
        <div class="waste-item-content">
          <div class="waste-item-label">${item.label}</div>
          <div class="waste-item-date">${item.dateHuman}</div>
        </div>
        ${this._config.show_days_badge ? `<div class="waste-item-badge ${item.badge.class}">${item.badge.text}</div>` : ''}
      </div>
    `;
  }

  _renderTimeline(items) {
    // Group by date
    const grouped = {};
    for (const item of items) {
      const key = item.date.toISOString().split('T')[0];
      if (!grouped[key]) {
        grouped[key] = {
          date: item.date,
          dateHuman: item.dateHuman,
          days: item.days,
          items: [],
        };
      }
      grouped[key].items.push(item);
    }

    const groups = Object.values(grouped).sort((a, b) => a.date - b.date).slice(0, 8);

    return `
      <div class="timeline">
        <div class="timeline-title">
          <ha-icon icon="mdi:calendar-clock"></ha-icon>
          <span>Nadcházející svozy</span>
        </div>
        <div class="timeline-list">
          ${groups.map(group => `
            <div class="timeline-row ${group.days === 0 ? 'is-today' : group.days === 1 ? 'is-tomorrow' : ''}">
              <div class="timeline-date">
                <div class="timeline-date-day">${group.date.getDate()}</div>
                <div class="timeline-date-month">${MONTHS_CS[group.date.getMonth()].substring(0, 3)}</div>
              </div>
              <div class="timeline-connector">
                <div class="timeline-dot"></div>
                <div class="timeline-line"></div>
              </div>
              <div class="timeline-content">
                <div class="timeline-day-name">${DAYS_CS[group.date.getDay()]}</div>
                <div class="timeline-chips">
                  ${group.items.map(ti => `
                    <span class="timeline-chip" style="--chip-color: ${ti.color}; --chip-bg-light: ${ti.bgLight}; --chip-bg-dark: ${ti.bgDark}">
                      <ha-icon icon="${ti.icon}"></ha-icon>
                      ${ti.label}
                    </span>
                  `).join('')}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _getStyles() {
    return `
      :host {
        --card-bg: var(--ha-card-background, var(--card-background-color, #fff));
        --primary-text: var(--primary-text-color, #1a1a2e);
        --secondary-text: var(--secondary-text-color, #6b7280);
        --divider: var(--divider-color, #e5e7eb);
      }

      ha-card {
        overflow: hidden;
        border-radius: var(--ha-card-border-radius, 12px);
      }

      /* ── Header ── */
      .card-header {
        padding: 20px 20px 16px;
        background: var(--card-bg);
        border-bottom: 1px solid var(--divider);
      }

      .header-content {
        display: flex;
        align-items: center;
        gap: 14px;
      }

      .header-icon {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--accent-gradient, linear-gradient(135deg, #6366f1, #8b5cf6));
        color: #fff;
        flex-shrink: 0;
      }

      .header-icon ha-icon {
        --mdc-icon-size: 22px;
        color: #fff;
      }

      .header-text {
        flex: 1;
        min-width: 0;
      }

      .header-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text);
        line-height: 1.3;
      }

      .header-subtitle {
        font-size: 13px;
        color: var(--secondary-text);
        margin-top: 2px;
        line-height: 1.4;
      }

      .header-subtitle strong {
        color: var(--primary-text);
      }

      .header-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        flex-shrink: 0;
        white-space: nowrap;
      }

      /* ── Card Content ── */
      .card-content {
        padding: 16px;
      }

      .card-content.compact {
        padding: 12px;
      }

      /* ── Waste Grid ── */
      .waste-grid {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .waste-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 12px;
        background: var(--item-bg-light);
        position: relative;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }

      .waste-item:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      }

      .waste-item.is-next {
        box-shadow: 0 0 0 2px var(--item-color), 0 4px 16px rgba(0,0,0,0.08);
      }

      .waste-item.is-today {
        animation: pulse-glow 2s ease-in-out infinite;
      }

      @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 0 2px var(--item-color), 0 0 8px rgba(0,0,0,0.06); }
        50% { box-shadow: 0 0 0 3px var(--item-color), 0 0 20px color-mix(in srgb, var(--item-color) 25%, transparent); }
      }

      .waste-item-indicator {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: var(--item-gradient);
        border-radius: 0 4px 4px 0;
      }

      .waste-item-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--item-gradient);
        flex-shrink: 0;
      }

      .waste-item-icon ha-icon {
        --mdc-icon-size: 18px;
        color: #fff;
      }

      .waste-item-content {
        flex: 1;
        min-width: 0;
      }

      .waste-item-label {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text);
        line-height: 1.3;
      }

      .waste-item-date {
        font-size: 12px;
        color: var(--secondary-text);
        margin-top: 1px;
      }

      .waste-item-badge {
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 11px;
        font-weight: 600;
        flex-shrink: 0;
        white-space: nowrap;
      }

      /* Badge variants */
      .badge-today {
        background: #FEE2E2;
        color: #DC2626;
      }

      .badge-tomorrow {
        background: #FEF3C7;
        color: #D97706;
      }

      .badge-future {
        background: #DBEAFE;
        color: #2563EB;
      }

      .badge-neutral {
        background: #F3F4F6;
        color: #6B7280;
      }

      /* Dark mode badge adjustments */
      @media (prefers-color-scheme: dark) {
        .badge-today {
          background: rgba(220, 38, 38, 0.2);
          color: #FCA5A5;
        }
        .badge-tomorrow {
          background: rgba(217, 119, 6, 0.2);
          color: #FCD34D;
        }
        .badge-future {
          background: rgba(37, 99, 235, 0.2);
          color: #93C5FD;
        }
        .badge-neutral {
          background: rgba(107, 114, 128, 0.2);
          color: #9CA3AF;
        }
        .waste-item {
          background: var(--item-bg-dark);
        }
      }

      /* Also handle HA dark mode via theme */
      :host-context([data-theme="dark"]) .badge-today,
      :host-context(.dark) .badge-today {
        background: rgba(220, 38, 38, 0.2);
        color: #FCA5A5;
      }

      :host-context([data-theme="dark"]) .badge-tomorrow,
      :host-context(.dark) .badge-tomorrow {
        background: rgba(217, 119, 6, 0.2);
        color: #FCD34D;
      }

      :host-context([data-theme="dark"]) .badge-future,
      :host-context(.dark) .badge-future {
        background: rgba(37, 99, 235, 0.2);
        color: #93C5FD;
      }

      :host-context([data-theme="dark"]) .badge-neutral,
      :host-context(.dark) .badge-neutral {
        background: rgba(107, 114, 128, 0.2);
        color: #9CA3AF;
      }

      :host-context([data-theme="dark"]) .waste-item,
      :host-context(.dark) .waste-item {
        background: var(--item-bg-dark);
      }

      /* ── Timeline ── */
      .timeline {
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--divider);
      }

      .timeline-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 14px;
      }

      .timeline-title ha-icon {
        --mdc-icon-size: 16px;
      }

      .timeline-list {
        display: flex;
        flex-direction: column;
        gap: 0;
      }

      .timeline-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        min-height: 52px;
      }

      .timeline-date {
        width: 40px;
        text-align: center;
        flex-shrink: 0;
        padding-top: 2px;
      }

      .timeline-date-day {
        font-size: 18px;
        font-weight: 700;
        color: var(--primary-text);
        line-height: 1.1;
      }

      .timeline-date-month {
        font-size: 10px;
        color: var(--secondary-text);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 1px;
      }

      .timeline-row.is-today .timeline-date-day {
        color: #DC2626;
      }

      .timeline-row.is-tomorrow .timeline-date-day {
        color: #D97706;
      }

      .timeline-connector {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex-shrink: 0;
        padding-top: 6px;
      }

      .timeline-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--divider);
        border: 2px solid var(--card-bg);
        box-shadow: 0 0 0 2px var(--divider);
        flex-shrink: 0;
      }

      .timeline-row.is-today .timeline-dot {
        background: #DC2626;
        box-shadow: 0 0 0 2px #FCA5A5;
      }

      .timeline-row.is-tomorrow .timeline-dot {
        background: #D97706;
        box-shadow: 0 0 0 2px #FCD34D;
      }

      .timeline-line {
        width: 2px;
        flex: 1;
        background: var(--divider);
        min-height: 20px;
      }

      .timeline-row:last-child .timeline-line {
        display: none;
      }

      .timeline-content {
        flex: 1;
        min-width: 0;
        padding-bottom: 14px;
      }

      .timeline-day-name {
        font-size: 12px;
        color: var(--secondary-text);
        margin-bottom: 4px;
      }

      .timeline-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .timeline-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 11px;
        font-weight: 600;
        background: var(--chip-bg-light);
        color: var(--chip-color);
      }

      .timeline-chip ha-icon {
        --mdc-icon-size: 13px;
      }

      @media (prefers-color-scheme: dark) {
        .timeline-chip {
          background: var(--chip-bg-dark);
        }
      }

      :host-context([data-theme="dark"]) .timeline-chip,
      :host-context(.dark) .timeline-chip {
        background: var(--chip-bg-dark);
      }

      /* ── Compact mode ── */
      .compact .waste-item {
        padding: 8px 12px;
      }

      .compact .waste-item-icon {
        width: 30px;
        height: 30px;
        border-radius: 8px;
      }

      .compact .waste-item-icon ha-icon {
        --mdc-icon-size: 15px;
      }

      .compact .waste-item-label {
        font-size: 13px;
      }

      .compact .waste-item-date {
        font-size: 11px;
      }
    `;
  }

  getCardSize() {
    return this._config.show_timeline ? 5 : 3;
  }
}

// ── Card Editor ──
class TurnovTridiCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        .editor {
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        label {
          font-size: 13px;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        input[type="text"] {
          padding: 8px 12px;
          border: 1px solid var(--divider-color, #ddd);
          border-radius: 8px;
          font-size: 14px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }
      </style>
      <div class="editor">
        <div class="row">
          <label>Entity (senzor nejbližšího svozu)</label>
          <input type="text" id="entity" value="${this._config.entity || ''}" placeholder="sensor.svoz_odpadu_karovsko_nejblizsi_svoz">
        </div>
        <div class="row">
          <label>Název karty</label>
          <input type="text" id="title" value="${this._config.title || 'Svoz odpadu'}">
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_header" ${this._config.show_header !== false ? 'checked' : ''}>
          <label for="show_header">Zobrazit hlavičku</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_timeline" ${this._config.show_timeline !== false ? 'checked' : ''}>
          <label for="show_timeline">Zobrazit časovou osu</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="compact" ${this._config.compact ? 'checked' : ''}>
          <label for="compact">Kompaktní režim</label>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById('entity').addEventListener('change', (e) => {
      this._updateConfig('entity', e.target.value);
    });
    this.shadowRoot.getElementById('title').addEventListener('change', (e) => {
      this._updateConfig('title', e.target.value);
    });
    this.shadowRoot.getElementById('show_header').addEventListener('change', (e) => {
      this._updateConfig('show_header', e.target.checked);
    });
    this.shadowRoot.getElementById('show_timeline').addEventListener('change', (e) => {
      this._updateConfig('show_timeline', e.target.checked);
    });
    this.shadowRoot.getElementById('compact').addEventListener('change', (e) => {
      this._updateConfig('compact', e.target.checked);
    });
  }

  _updateConfig(key, value) {
    this._config = { ...this._config, [key]: value };
    const event = new CustomEvent('config-changed', {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define('turnov-tridi-card', TurnovTridiCard);
customElements.define('turnov-tridi-card-editor', TurnovTridiCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'turnov-tridi-card',
  name: 'Turnov Třídí – Svoz odpadu',
  description: 'Přehledná karta zobrazující termíny svozu odpadu v Turnově.',
  preview: true,
  documentationURL: 'https://github.com/DavidLouda/turnov-tridi-hacs',
});

console.info(
  '%c TURNOV-TŘÍDÍ-CARD %c v1.0.0 ',
  'color: white; background: #10B981; font-weight: bold; padding: 2px 6px; border-radius: 4px 0 0 4px;',
  'color: #10B981; background: #ECFDF5; font-weight: bold; padding: 2px 6px; border-radius: 0 4px 4px 0;',
);
