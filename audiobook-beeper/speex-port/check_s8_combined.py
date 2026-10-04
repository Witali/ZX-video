"""Full word-domain checks and instruction-derived costs for the selected signed8 core."""
import argparse
from collections import Counter
import json
from check_primitives import call,machine,symbols
from verify import ROOT


def expected_cost(a,b):
    if not a:return 41
    magnitude=abs(a);bits=magnitude.bit_length()
    # Sign handling/return: 112 T for positive A, 176 T for negative A;
    # negative DE takes one fewer T (untaken JR + SUB instead of taken JR).
    # Core: LD A,B=4; each skipped zero=11; first one with transfer=34;
    # each remaining zero=27, each remaining one adds 13 T to that.
    return ((176 if a<0 else 112)+4+11*(8-bits)+34+27*(bits-1)
            +13*(magnitude.bit_count()-1)-(b<0))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',default='pure-r18-signed');a=p.parse_args()
    folder=ROOT/'build/speex-port'/a.variant;m=machine(folder);s=symbols(folder)
    rows=[];hist=Counter()
    for signed_byte in (-128,-127,-65,-1,0,1,65,97,127):
        costs=Counter()
        for word in range(-32768,32768):
            cost=call(m,s['_mul_s8'],a=signed_byte&255,de=word&65535)
            assert (m.hl<<16|m.de)==(signed_byte*word)&0xffffffff,(signed_byte,word)
            assert cost==expected_cost(signed_byte,word),(signed_byte,word,cost)
            costs[cost]+=1
        rows.append(dict(multiplier=signed_byte,words=65536,tstates=dict(sorted(costs.items()))))
        hist.update(costs)
        print('Complete word domain passed for multiplier',signed_byte,flush=True)
    result=dict(exact_products=9*65536,all_costs_match_instruction_formula=True,
                cases=rows,tstates=dict(sorted(hist.items())))
    (folder/'s8-domain-checks.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
