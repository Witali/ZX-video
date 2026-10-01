"""Renumbering preserves dynamic replacements, packet operations and screens."""
import unittest
import itertools

from dynamic_row_dictionary import decode_check
from front_cell_reuse import representation
from partial_row_cells import encode
from probe_dictionary_numbering import locations,remap
from test_dynamic_row_dictionary import fixture


class NumberingTests(unittest.TestCase):
    def test_short_match_costs_against_complete_reserialization(self):
        from fit_lzsa2_cpu_budget import model
        from lzsa2_distance_cost import Costs
        from lzsa2_oracle import encode as pack
        from optimize_lzsa2_distances import candidates,parse,evaluate
        costs=Costs();checked=0
        for raw in (b'A'*10,b'AB'*6,b'ABC'*4,b'AABAABAAB',b'ABCDEFGHI'):
            ps=[p for p in range(1,len(raw)-1) if candidates(raw,p,2)]
            for count in range(4):
                for selected in itertools.combinations(ps,count):
                    if any(b<a+2 for a,b in zip(selected,selected[1:])):continue
                    matches=[(p,2,candidates(raw,p,2)[-1]) for p in selected]
                    proposed,_,_=model(matches,len(raw),costs)
                    for choice in proposed:
                        remaining=matches[:choice['index']]+matches[choice['index']+1:]
                        payload=pack(raw,remaining);_,rows,tail=parse(payload,len(raw))
                        units,ticks=evaluate(rows,[r['distance'] for r in rows],tail,costs)
                        self.assertEqual((len(payload),units,ticks),(choice['bytes'],choice['nibbles'],choice['token_tstates']))
                        checked+=1
        self.assertGreater(checked,100)

    def test_replacements_and_independent_volume_history(self):
        frames=fixture()
        for start,end in ((0,12),(3,11)):
            base=encode(representation(frames,start,end),frames,start,end)
            self.assertGreater(base['proof']['row_updates'],0)
            for kind in ('rows','aligned','flat'):
                data,rows,maps=remap(base['raw'],base['rows'],kind)
                self.assertEqual(decode_check(data,frames,start,end,rows),base['proof'])
                self.assertEqual(maps['rows'][0],0)
                rp,bp=locations(base['raw']);self.assertEqual(locations(data),(rp,bp))
                changed=set(rp+bp)
                self.assertTrue(all(data[i]==base['raw'][i] for i in range(2056,len(data)) if i not in changed))
                self.assertEqual(len(data),len(base['raw']))


if __name__=='__main__':unittest.main()
