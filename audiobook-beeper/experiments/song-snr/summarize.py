"""Publish whole-corpus comparisons and identify every regression explicitly."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    a=p.parse_args();root=a.directory;report=json.loads((root/'report.json').read_bytes());assert report['complete']
    rows=[]
    for record in report['rows']:
        source=record['source'];base=next(x for x in record['models'] if x['model']=='legacy')
        for row in record['models']:
            before=base['total_on_shared_clock'];after=row['total_on_shared_clock']
            delta=10*np.log10(before['error_power']/after['error_power'])
            rows.append(dict(source=source['name'],split=source['split'],model=row['model'],
                             pdm_snr_db=row['pdm_only']['snr_db'],total_shared_clock_snr_db=after['snr_db'],
                             total_error_improvement_db=float(delta),regression=bool(delta<-.01),
                             absolute_noise_rms=after['error_rms'],layout_fits=row['layout_fits']))
    with (root/'comparison.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    regressions=[r for r in rows if r['regression']]
    decisions=dict(complete=True,comparison_scope='Host shared-clock total-error controls; not measured fixed-clock disk SNR',
                   regressions=regressions,unconditional_table_replacement_accepted=False,
                   new_release_or_main_changes=False,
                   reason='No table control improves every tested signal; beneficial duration-aware dictionaries exceed current fixed layout',
                   next_mechanism='Generic clock-aware joint IMA/PDM encoding with measured baseline fallback, plus a verified layout for wider dictionaries',
                   source_specific_tuning_allowed=False)
    save(root/'decision.json',decisions)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        names=[r['source']['name'] for r in report['rows']];x=np.arange(len(names));fig,ax=plt.subplots(figsize=(11,4.8))
        for j,(label,color) in enumerate([('duration_midpoint','#2474a5'),('duration_zero_half_recent','#e58b30')]):
            scores=[next(r['total_error_improvement_db'] for r in rows if r['source']==name and r['model']==label) for name in names]
            ax.bar(x+(j-.5)*.34,scores,width=.32,label=label.replace('_',' '),color=color)
        ax.axhline(0,color='#333333',linewidth=.8);ax.set_xticks(x,names,rotation=25,ha='right')
        ax.set_ylabel('Total error reduction vs legacy (dB)');ax.set_title('Generic PDM controls: whole sources, common parameters')
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='upper right')
        fig.text(.02,.01,'Host instruction-derived Pentagon clock. Silence uses absolute error power. No new player execution or release claim.',fontsize=8)
        fig.tight_layout(rect=(0,.055,1,1));fig.savefig(root/'comparison.png',dpi=150);plt.close(fig)
    except ImportError:pass
    print(json.dumps(dict(rows=len(rows),regressions=len(regressions))),flush=True)


if __name__=='__main__':main()
