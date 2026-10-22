"""Minimal R12 DXF reader (cp932) + matplotlib renderer."""
import math


def parse(path):
    lines = open(path, 'rb').read().decode('cp932', errors='replace').splitlines()
    pairs = [(lines[i].strip(), lines[i + 1]) for i in range(0, len(lines) - 1, 2)]
    ents = []
    cur = None
    inent = False
    for c, v in pairs:
        if c == '2' and v == 'ENTITIES':
            inent = True
            continue
        if not inent:
            continue
        if c == '0':
            if cur:
                ents.append(cur)
            if v == 'ENDSEC':
                break
            cur = {'type': v, 'tags': []}
        else:
            cur['tags'].append((c, v))
    out = []
    for e in ents:
        t = {}
        for c, v in e['tags']:
            t.setdefault(c, v)
        d = {'type': e['type'], 'layer': t.get('8'), 'color': int(t.get('62', 256))}
        f = lambda k, dflt=0.0: float(t.get(k, dflt))
        if e['type'] == 'LINE':
            d.update(p1=(f('10'), f('20')), p2=(f('11'), f('21')))
        elif e['type'] == 'CIRCLE':
            d.update(c=(f('10'), f('20')), r=f('40'))
        elif e['type'] == 'ARC':
            d.update(c=(f('10'), f('20')), r=f('40'), a0=f('50'), a1=f('51'))
        elif e['type'] == 'TEXT':
            d.update(p=(f('10'), f('20')), h=f('40'), rot=f('50'), text=t.get('1', ''),
                     p11=(f('11'), f('21')) if '11' in t else None,
                     h72=int(t.get('72', 0)), v73=int(t.get('73', 0)))
        else:
            d['tags'] = e['tags']
        out.append(d)
    return out


ACI = {1: 'red', 2: 'gold', 3: 'green', 4: 'c', 5: 'blue', 6: 'm', 7: 'k', 8: 'gray', 9: 'silver',
       30: 'orange', 132: 'teal', 212: 'purple', 256: 'k'}


def render(ents, png, xlim=None, ylim=None, size=(28, 20), dpi=100, color_by_layer=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import Arc, Circle
    fp = font_manager.FontProperties(fname='/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
    fig, ax = plt.subplots(figsize=size)
    for e in ents:
        col = ACI.get(e['color'], 'k')
        if color_by_layer and e['layer'] in color_by_layer:
            col = color_by_layer[e['layer']]
        lw = 0.6
        if e['type'] == 'LINE':
            ax.plot([e['p1'][0], e['p2'][0]], [e['p1'][1], e['p2'][1]], color=col, lw=lw)
        elif e['type'] == 'CIRCLE':
            ax.add_patch(Circle(e['c'], e['r'], fill=False, color=col, lw=lw))
        elif e['type'] == 'ARC':
            ax.add_patch(Arc(e['c'], 2 * e['r'], 2 * e['r'], theta1=e['a0'], theta2=e['a1'], color=col, lw=lw))
        elif e['type'] == 'TEXT':
            p = e['p11'] if (e.get('p11') and (e['h72'] or e['v73'])) else e['p']
            ha = {0: 'left', 1: 'center', 2: 'right', 4: 'center'}.get(e['h72'], 'left')
            va = {0: 'baseline', 1: 'bottom', 2: 'center', 3: 'top'}.get(e['v73'], 'baseline')
            if e['h72'] == 4:
                va = 'center'
            ax.text(p[0], p[1], e['text'], fontproperties=fp, fontsize=max(e['h'] / 25, 3),
                    rotation=e['rot'], ha=ha, va=va, color=col)
    ax.set_aspect('equal')
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.autoscale_view()
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, lw=0.2)
    fig.tight_layout()
    fig.savefig(png, dpi=dpi)
    plt.close(fig)
