#!/usr/bin/env python3
"""Generic saved-data plotting helper; evidence and event mapping belong to caller."""
import argparse
import datetime as dt
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as dates
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('input', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
views = json.loads(a.input.read_text())['views']
when = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
a.output.mkdir(parents=True, exist_ok=True)
for theme in ('light', 'dark'):
    bg, fg, accent = ('#ffffff', '#0f172a', '#0e7490') if theme == 'light' else ('#0f172a', '#f1f5f9', '#67e8f9')
    with plt.rc_context({'font.size': 11, 'svg.fonttype': 'none', 'svg.hashsalt': 'correlation-fixture'}):
        for index, v in enumerate(views, 1):
            fig, (ax, lane) = plt.subplots(2, 1, figsize=(13, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]}, layout='constrained')
            fig.patch.set_facecolor(bg)
            for axis in (ax, lane):
                axis.set_facecolor(bg)
                axis.tick_params(colors=fg)
                for spine in axis.spines.values():
                    spine.set_color(fg)
                axis.xaxis.label.set_color(fg)
                axis.yaxis.label.set_color(fg)
                axis.xaxis.set_major_formatter(dates.DateFormatter('%H:%M', tz=dt.timezone.utc))
            ax.set_title(v['title'], color=fg, fontsize=11)
            ax.set_ylabel(v['ylabel'])
            ax.plot([when(x['time']) for x in v['points']], [float('nan') if x['value'] is None else x['value'] for x in v['points']], 'o-', color=accent)
            for i, e in enumerate(v.get('events', [])):
                lane.scatter([when(e['time'])], [i], marker='v', color=accent)
                lane.annotate(e['label'], (when(e['time']), i), xytext=(5, 4), textcoords='offset points', color=fg)
            lane.set_yticks([])
            lane.set_xlabel('UTC time')
            lane.set_ylim(-1, max(2, len(v.get('events', []))))
            for ext in ('svg', 'png'):
                fig.savefig(a.output / (str(index) + '-' + theme + '.' + ext), facecolor=bg)
            plt.close(fig)
