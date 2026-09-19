// mlrv-pd frontend mocks — shared site JS
// Tiny helpers used across pages. No framework.

window.MLRV = (function () {

  // Build an 8x8 monome grid into a container. Returns the grid element.
  // Each cell is data-level=0..15. Cells in the y=7 row get class .trigger.
  function buildGrid(container, opts = {}) {
    const grid = document.createElement('div');
    grid.className = 'grid';
    const cells = [];
    for (let y = 0; y < 8; y++) {
      for (let x = 0; x < 8; x++) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.x = x;
        cell.dataset.y = y;
        cell.dataset.level = '0';
        if (y === 7) cell.classList.add('trigger');
        cells.push(cell);
        grid.appendChild(cell);
      }
    }
    container.appendChild(grid);
    return { grid, cells };
  }

  function setLevel(cells, x, y, level) {
    const c = cells[y * 8 + x];
    if (c) c.dataset.level = String(Math.max(0, Math.min(15, level)));
  }
  function clearAll(cells) {
    for (const c of cells) c.dataset.level = '0';
  }

  // Format ms timestamp.
  function ts() {
    const d = new Date();
    return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3,'0');
  }

  function appendLog(el, tag, msg) {
    const span = document.createElement('span');
    span.className = 'ev';
    span.innerHTML = `<span class="t">${ts()}</span><span class="tag ${tag}">${tag.padEnd(5,' ')}</span><span class="msg"></span>`;
    span.querySelector('.msg').textContent = msg;
    el.appendChild(span);
    el.scrollTop = el.scrollHeight;
    // cap the buffer at ~300 lines so the DOM stays small
    while (el.children.length > 300) el.removeChild(el.firstChild);
  }

  // Mini Pd-style object description for the patch graph sidebar.
  function describePdObj(name) {
    const map = {
      inlet:  'control inlet — receives messages from parent patch',
      outlet: 'control outlet — emits messages to parent patch',
      'inlet~': 'audio inlet (~) — receives a signal',
      'outlet~': 'audio outlet (~) — emits a signal',
      loadbang: 'fires `bang` once when the patch loads',
      route: 'routes input by first atom (selector)',
      unpack: 'splits a list into its constituent atoms',
      pack:  'packs multiple inlets into a list',
      't':    'trigger — fires its outlets (right-to-left)',
      float: 'stores and emits a float',
      symbol: 'stores and emits a symbol',
      msg:   'message — when banged, outputs its content',
      oscformat: 'formats a Pd message into OSC bytes',
      oscparse: 'parses an OSC packet into a Pd list',
      netsend: 'UDP/TCP sender',
      netreceive: 'UDP/TCP receiver',
      print: 'prints incoming messages to the Pd console',
      table: 'named sample/array buffer',
      'play_loop~': 'phasor-driven loop player',
      'sample_voice~': 'one voice = one play_loop~ + envelope',
      serialosc: 'OSC bridge to monome serialosc daemon',
      grid:   'LED passthrough / coordinate helper',
      mapping:'grid-key → play/stop action translator',
      file_poly: '8 sample slots × 4-voice polyphonic player',
      master: 'master output bus + soft-clip + meter',
      mixer:  '4-channel mixer (not wired in mlrv.pd yet)',
      'dac~': 'soundcard output (channels 1,2 = L,R)',
      'sig~': 'constant signal value',
      'send~': 'send a signal to a named receive~ (one-block lag)',
      'receive~': 'receive a signal from a named send~',
      'line~': 'smooth ramp between target values',
      '*~':   'signal multiply',
      '+~':   'signal add',
      'expr~':'per-sample expression evaluator',
      'abs~': 'absolute value of a signal',
      'env~': 'RMS envelope follower',
      'soundfiler': 'read/write audio from/to a table',
      'makefilename': 'format a string with %d substitution',
      'min':  'minimum of two floats',
      'max':  'maximum of two floats',
      'mod':  'modulo (wrap-around)',
      '+':    'add',
    };
    return map[name] || ('Pd object — see Pd docs for `' + name + '`');
  }

  return { buildGrid, setLevel, clearAll, appendLog, ts, describePdObj };
})();
