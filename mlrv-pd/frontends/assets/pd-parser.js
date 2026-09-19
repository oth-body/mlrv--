// Tiny .pd file parser → graph for the patch-graph frontend.
// Pure stdlib JS, no deps. Reads the `#X obj`/`#X msg`/`#X text`/`#X connect`
// lines a vanilla .pd file uses (the same ones the existing patches use).
//
// We only model *what the user can see and click*: object boxes by id, their
// class name, their 2D position, and which connections exist between them.
// Pd stores connection indices by *file order*, which we honor exactly —
// this is the same load-bearing detail CLAUDE.md warns about, and rendering
// the file at all is itself a check that nothing's been silently renumbered.

window.MLRV_PD = (function () {

  function parse(text) {
    const lines = text.split('\n');
    const objs = [];           // [{ idx, kind, x, y, args: [] }]
    const connects = [];       // [{ fromObj, fromOut, toObj, toIn }]
    const tables = [];         // ['mlrv-sample-0', ...]
    let canvas = { x:0, y:0, w:600, h:400 };

    for (const raw of lines) {
      const line = raw.trim();
      if (!line || line.startsWith('#N canvas')) {
        if (line.startsWith('#N canvas')) {
          const parts = line.split(/\s+/);
          // #N canvas X Y W HEIGHT
          if (parts.length >= 6) {
            canvas = {
              x: +parts[2], y: +parts[3],
              w: +parts[4], h: +parts[5],
            };
          }
        }
        continue;
      }
      // Tokenize the #X line.
      const tok = line.split(/\s+/);
      const kind = tok[1];

      if (kind === 'obj') {
        // #X obj X Y CLASSNAME ARGS...
        // Pd uses `;` to terminate the line and start an in-line comment.
        const x = +tok[2], y = +tok[3];
        let cls = tok[4];
        if (cls && cls.endsWith(';')) cls = cls.slice(0, -1);
        // Strip trailing `;` from each arg (some files do per-arg comments)
        const args = tok.slice(5).map(a => a && a.endsWith(';') ? a.slice(0,-1) : a);
        const idx = objs.length;
        const audio = cls.endsWith('~') || cls === 'dac~' || cls === 'adc~';
        const isIO = (cls === 'inlet' || cls === 'outlet' || cls === 'inlet~' || cls === 'outlet~');
        objs.push({ idx, kind: 'obj', x, y, cls, args, audio, isIO });
        if (cls === 'table') tables.push(args[0]);
      } else if (kind === 'msg') {
        const x = +tok[2], y = +tok[3];
        // Pd msg lines end with `;` (the message terminator).
        let content = tok.slice(4).join(' ');
        if (content.endsWith(';')) content = content.slice(0, -1);
        const idx = objs.length;
        objs.push({ idx, kind: 'msg', x, y, cls: 'msg', args: [content] });
      } else if (kind === 'text') {
        const x = +tok[2], y = +tok[3];
        const content = tok.slice(4).join(' ');
        const idx = objs.length;
        objs.push({ idx, kind: 'text', x, y, cls: 'text', args: [content] });
      } else if (kind === 'connect') {
        connects.push({
          fromObj: +tok[2], fromOut: +tok[3],
          toObj:   +tok[4], toIn:   +tok[5],
        });
      } else if (kind === 'array') {
        // #X array NAME SIZE X Y ...
        // Not used by these patches but parse anyway.
      }
    }

    return { canvas, objs, connects, tables };
  }

  // Layout pass: Pd stores X,Y for the *top-left* of the box; we need to know
  // each box's width/height to draw and to route connections to its inlet/outlet
  // sockets. Estimate box width from the longest label token.
  function boxSize(obj) {
    let label;
    if (obj.kind === 'msg') label = obj.args[0] || '';
    else if (obj.kind === 'text') label = (obj.args[0] || '').slice(0, 24);
    else label = [obj.cls, ...obj.args].join(' ');
    // Approx 7px per char + padding
    const w = Math.max(48, Math.min(220, 8 + label.length * 6.6));
    const h = obj.kind === 'text' ? 14 : 22;
    return { w, h };
  }

  // Socket positions: Pd objects have a default of 1 inlet + 1 outlet; some
  // (unpack, route, oscformat, msg with $N, multi-arg abstractions) have more.
  // We expose inlet/outlet counts on demand from the parsed object.
  function socketCount(obj) {
    if (obj.kind === 'text') return { ins: 0, outs: 0 };
    const a = obj.args;
    switch (obj.cls) {
      case 'route':     return { ins: 1, outs: a.length };
      case 'unpack':    return { ins: 1, outs: a.length };
      case 'pack':      return { ins: a.length, outs: 1 };
      case 't':
      case 'trigger':   return { ins: 1, outs: a.length };
      case 'oscparse':  return { ins: 1, outs: 1 };
      case 'oscformat': return { ins: 1, outs: 1 };
      case 'netsend':   return { ins: 2, outs: 0 };
      case 'netreceive':return { ins: 0, outs: 1 };
      case 'msg':       return { ins: 1, outs: 1 };
      case 'print':     return { ins: 1, outs: 0 };
      case 'float':     return { ins: 1, outs: 1 };
      case 'symbol':    return { ins: 1, outs: 1 };
      case '+': case 'min': case 'max': case 'mod':
        return { ins: 2, outs: 1 };
      case '*':         return { ins: 2, outs: 1 };
      case 'soundfiler':return { ins: 2, outs: 0 };
      case 'makefilename': return { ins: 1, outs: 1 };
      case 'inlet':     return { ins: 0, outs: 1 };
      case 'outlet':    return { ins: 1, outs: 0 };
      case 'inlet~':    return { ins: 0, outs: 1 };
      case 'outlet~':   return { ins: 1, outs: 0 };
      case 'loadbang':  return { ins: 0, outs: 1 };
      case 'dac~':      return { ins: a.length, outs: 0 };
      case 'adc~':      return { ins: 0, outs: a.length };
      case 'sig~':      return { ins: 0, outs: 1 };
      case 'send~':     return { ins: 1, outs: 0 };
      case 'receive~':  return { ins: 0, outs: 1 };
      case 'line~':     return { ins: 1, outs: 1 };
      case '*~': case '+~':
      case 'abs~': case 'min~': case 'max~':
        return { ins: 2, outs: 1 };
      case 'expr~':     return { ins: 1, outs: 1 };
      case 'env~':      return { ins: 1, outs: 1 };
      case 'tabread':   return { ins: 1, outs: 1 };
      case 'tabwrite':  return { ins: 1, outs: 0 };
      case 'tabread4~': return { ins: 1, outs: 1 };
      case 'tabwrite~': return { ins: 1, outs: 0 };
      case 'phasor~':   return { ins: 0, outs: 1 };
      case 'samplerate~':return { ins: 0, outs: 1 };
      default:
        // Generic abstraction — show 1 in / 1 out unless we know otherwise.
        return { ins: 1, outs: 1 };
    }
  }

  function inletPos(obj, n) {
    const s = boxSize(obj);
    const c = socketCount(obj);
    const yoff = 6;
    if (c.ins <= 1) return { x: obj.x, y: obj.y + s.h / 2 };
    const step = (s.h - 12) / Math.max(1, c.ins - 1);
    return { x: obj.x, y: obj.y + yoff + n * step };
  }
  function outletPos(obj, n) {
    const s = boxSize(obj);
    const c = socketCount(obj);
    if (c.outs <= 1) return { x: obj.x + s.w, y: obj.y + s.h / 2 };
    const step = (s.h - 12) / Math.max(1, c.outs - 1);
    return { x: obj.x + s.w, y: obj.y + 6 + n * step };
  }

  // Render an entire parsed graph to an <svg>.
  function renderSVG(graph) {
    const { canvas, objs, connects } = graph;
    const pad = 30;
    const W = Math.max(canvas.w + pad * 2, 600);
    const H = Math.max(canvas.h + pad * 2, 360);

    let svg = `<svg class="pd" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">`;
    svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="#07080a"/>`;

    // Edges first so they sit under the boxes.
    for (const c of connects) {
      const from = objs[c.fromObj];
      const to   = objs[c.toObj];
      if (!from || !to) continue;
      const p1 = outletPos(from, c.fromOut);
      const p2 = inletPos(to, c.toIn);
      const sig = from.audio || to.audio;
      const dx = Math.max(20, (p2.x - p1.x) * 0.5);
      const path = `M${p1.x} ${p1.y} C${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;
      svg += `<path class="connect${sig ? ' sig' : ''}" d="${path}" data-from="${c.fromObj}" data-to="${c.toObj}"/>`;
    }

    // Boxes
    for (const o of objs) {
      if (o.kind === 'text') {
        // Plain comment text — no box.
        const lines = (o.args[0] || '').split(/\\,/).map(s => s.trim());
        for (let i = 0; i < lines.length; i++) {
          svg += `<text x="${o.x}" y="${o.y + 12 + i * 13}" fill="#9097a3" font-family="JetBrains Mono, monospace" font-size="10.5">${escapeXml(lines[i].slice(0, 200))}</text>`;
        }
        continue;
      }
      const s = boxSize(o);
      const cls = o.cls;
      const audio = o.audio;
      const isIO = o.isIO;
      const fillClass = audio ? 'sig' : (cls === 'msg' ? 'msg' : '');

      svg += `<g class="obj ${fillClass}" data-idx="${o.idx}" data-cls="${escapeXml(cls)}" transform="translate(0,0)">`;
      // Body
      if (cls === 'inlet' || cls === 'outlet' || cls === 'inlet~' || cls === 'outlet~') {
        svg += `<circle cx="${o.x + 6}" cy="${o.y + 8}" r="5" fill="${cls.startsWith('outlet') ? '#4ade80' : '#f5b942'}" stroke="#2e323d"/>`;
      } else {
        svg += `<rect x="${o.x}" y="${o.y}" width="${s.w}" height="${s.h}" rx="3"/>`;
        let label = '';
        if (cls === 'msg') label = (o.args[0] || '').slice(0, 24);
        else label = cls + (o.args.length ? ' ' + o.args.slice(0,3).join(' ') : '');
        svg += `<text x="${o.x + s.w/2}" y="${o.y + s.h/2 + 4}" text-anchor="middle">${escapeXml(label)}</text>`;
      }
      // Inlets (small squares on left edge)
      const ins = socketCount(o).ins;
      for (let i = 0; i < ins; i++) {
        const p = inletPos(o, i);
        svg += `<rect x="${p.x - 3}" y="${p.y - 3}" width="6" height="6" fill="${audio ? '#a0c4ff' : '#f5b942'}" stroke="#2e323d"/>`;
      }
      const outs = socketCount(o).outs;
      for (let i = 0; i < outs; i++) {
        const p = outletPos(o, i);
        svg += `<rect x="${p.x - 3}" y="${p.y - 3}" width="6" height="6" fill="${audio ? '#a0c4ff' : '#4ade80'}" stroke="#2e323d"/>`;
      }
      svg += `</g>`;
    }

    svg += `</svg>`;
    return svg;
  }

  function escapeXml(s) {
    return String(s).replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;'}[c]));
  }

  return { parse, renderSVG, boxSize, socketCount };
})();
