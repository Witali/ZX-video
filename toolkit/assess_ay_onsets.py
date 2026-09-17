"""Calculate 95% onset-F1 feasibility without changing the acceptance metric.

Count bounds are optimistic: removing one false detection must not remove a
true one. Timing-grid feasibility is not a proof that AY can retain all the
source timbres, pitches and envelopes, or that an encoder can find them.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np

import build_long_video_trd as video
import compare_ay_fidelity as quality


def count_bounds(reference,candidate,matched,target=Fraction(19,20)):
    if not 0<=matched<=min(reference,candidate) or reference<1:
        raise ValueError('invalid onset counts')
    numerator,denominator=target.numerator,target.denominator
    def passes(m,c):return 2*m*denominator>=numerator*(reference+c)
    solutions=[]
    for recovered in range(reference-matched+1):
        for removed in range(candidate-matched+1):
            m=matched+recovered;c=candidate+recovered-removed
            if passes(m,c):
                solutions.append(dict(recovered=recovered,removed=removed,matched=m,
                                      candidate=c,f1=2*m/(reference+c),edits=recovered+removed))
                break
    minimal=min(s['edits'] for s in solutions)
    return dict(reference=reference,candidate=candidate,matched=matched,
        false_positives=candidate-matched,false_negatives=reference-matched,
        f1=2*matched/(reference+candidate),
        retiming_only_upper_bound=2*min(reference,candidate)/(reference+candidate),
        remove_false_positives_only_upper_bound=2*matched/(reference+matched),
        minimum_matches_with_no_false_positives=next(m for m in range(reference+1) if passes(m,m)),
        maximum_candidates_with_all_reference_matched=(2*reference*denominator)//numerator-reference,
        minimum_detection_edits=minimal,
        best_case_edit_solutions=[s for s in solutions if s['edits']==minimal],
        balanced_candidate_case=dict(candidate=reference,
            minimum_matches=(numerator*reference+denominator-1)//denominator),
        scope='optimistic detection-count bounds, not achievable sound-quality guarantees')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rate-report',type=Path,required=True)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    experiment=json.loads(args.rate_report.read_text())
    rate=50;metric_rate=experiment['metric_rate_hz'];sample_rate=22050
    duration=experiment['duration_seconds']
    samples=video.decode_analysis_audio(args.ffmpeg,args.input_video,0,duration,sample_rate,True)
    digest=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()
    if digest!=experiment['source_pcm_sha256']:raise ValueError('different reference PCM')
    features=quality.features(samples,sample_rate,metric_rate,round(duration*metric_rate))
    indices=quality.onsets(features[0]);times=np.array(indices)/metric_rate
    quantized=np.rint(times*rate)/rate
    record=next(r for r in experiment['rates'] if r['update_rate_hz']==rate)
    counts=record['metrics']['onsets']
    if len(indices)!=counts['reference']:raise AssertionError('reference onset count changed')
    recovered_indices=np.rint(quantized*metric_rate).astype(int).tolist()
    timing_match=quality.match_onsets(indices,recovered_indices)
    result=dict(source_pcm_sha256=digest,duration_seconds=duration,threshold=.95,
        counts=count_bounds(counts['reference'],counts['candidate'],counts['matched']),
        timing_grid=dict(update_rate_hz=rate,tick_ms=1000/rate,
            arbitrary_event_nearest_tick_max_error_ms=500/rate,
            metric_tolerance_ms=experiment['onset_tolerance_seconds']*1000,
            measured_reference_min_separation_ms=float(np.min(np.diff(times))*1000),
            measured_reference_max_rounding_error_ms=float(np.max(np.abs(times-quantized))*1000),
            quantized_reference_onset_f1=timing_match['f1'],
            scope='ideal event scheduling only; metric-grid times, no synthesized audio'),
        reference_onset_seconds=times.tolist(),
        conclusion='50 Hz imposes no onset-timing barrier here. 95% F1 needs fewer false detections and fewer misses; end-to-end feasibility is not yet demonstrated.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='reference_onset_seconds'},indent=2))


if __name__=='__main__':main()
