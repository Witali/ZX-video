"""Compatibility import for the reusable ZX0 library."""
import codec_libraries  # Locate source packages in repository checkouts.
from zx0.resumable import *

def install_harness(h, variant):
    """CPU prototype only. Rebuild producer references; never patch a release TRD."""
    import inplace_slot_input_z80 as producer
    from test_fap3_disk import install
    regions,z,report=build(variant)
    c=h.cpu; c.decoding=False
    for at,data in regions:install(c,at,data)
    h.z=z; c.zlabels=z; c.patched=set(report['patched_addresses'])
    regions,p,rows=producer.build(z,h.d,elapsed_fields=h.elapsed_fields)
    for at,data in regions:install(c,at,data)
    h.p=p; h.regions=regions; h.instructions.update({r['address']:r for r in rows})
    return report
