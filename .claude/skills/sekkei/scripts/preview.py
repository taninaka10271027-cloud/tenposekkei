import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, Polygon
from matplotlib.collections import LineCollection

FP = font_manager.FontProperties(fname='/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf')
ACI = {1: '#e00000', 2: '#c8a000', 3: '#00a000', 4: '#00a0a0', 5: '#0000e0', 6: '#c000c0', 7: '#000000', 8: '#808080',
       9: '#a0a0a0', 30: '#ff8000', 40: '#ff9f00', 52: '#000000', 132: '#008080', 212: '#7000a0', 150: '#0060c0',
       11: '#ff6060', 21: '#c06000', 92: '#008000', 172: '#004080', 230: '#a00060', 200: '#6000c0', 34: '#b05000',
       70: '#606000', 140: '#0080a0', 190: '#8000a0', 250: '#404040', 10: '#ff0000', 160: '#2060a0', 60: '#808000',
       110: '#00a060', 240: '#c00040', 20: '#c04000', 130: '#00a0a0', 180: '#2040c0', 220: '#c000a0', 90: '#40a000'}


def col(c):
    return ACI.get(c, '#303030')


def render(ents, png, xlim=(0, 21000), ylim=(0, 14850), width_in=29.7, dpi=110, hide_layers=()):
    h_in = width_in * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0])
    fig = plt.figure(figsize=(width_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    segs, cols, ls = [], [], []
    for e in ents:
        if e['layer'] in hide_layers:
            continue
        c = col(e['color'])
        t = e['type']
        if t == 'LINE':
            ax.plot([e['p1'][0], e['p2'][0]], [e['p1'][1], e['p2'][1]], color=c, lw=0.5,
                    ls='--' if e.get('lt') in ('DASHED', 'HIDDEN') else ('-.' if e.get('lt') in ('CENTER', 'DASHDOT') else '-'))
        elif t == 'CIRCLE':
            ax.add_patch(Circle(e['c'], e['r'], fill=False, color=c, lw=0.5))
        elif t == 'ARC':
            ax.add_patch(Arc(e['c'], 2 * e['r'], 2 * e['r'], theta1=e['a0'], theta2=e['a1'], color=c, lw=0.5,
                             ls='--' if e.get('lt') in ('DASHED', 'HIDDEN') else '-'))
        elif t == 'SOLID':
            ax.add_patch(Polygon(e['pts'][:3] if e['pts'][2] == e['pts'][3] else [e['pts'][0], e['pts'][1], e['pts'][3], e['pts'][2]], closed=True, color=c))
        elif t == 'TEXT':
            ha = {0: 'left', 1: 'center', 2: 'right'}.get(e['h72'], 'left')
            va = {0: 'baseline', 1: 'bottom', 2: 'center', 3: 'top'}.get(e['v73'], 'baseline')
            # font size: model height -> points ; figure maps 21000 model -> width_in inches
            pts = e['h'] / (xlim[1] - xlim[0]) * width_in * 72 * 1.15
            ax.text(e['p'][0], e['p'][1], e['text'], fontproperties=FP, fontsize=max(pts, 1.5), rotation=e['rot'],
                    ha=ha, va=va, color=c, rotation_mode='anchor')
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.savefig(png, dpi=dpi, facecolor='white')
    plt.close(fig)
