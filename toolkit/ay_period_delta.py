"""Losslessly predict AY low period bytes before the existing Huffman coder."""
import ay_huffman_stream

PERIOD_LOW_REGISTERS=(0,2,4)


def transform(records,initial,*,decode=False):
    if len(initial)!=11:raise ValueError('expected eleven AY registers')
    previous=bytearray(initial);result=[]
    for record in records:
        if not record or len(record)!=1+2*record[0]:raise ValueError('invalid AY record')
        output=bytearray(record);seen=set()
        for at in range(1,len(record),2):
            register,value=record[at:at+2]
            if register>=11 or register in seen:raise ValueError('invalid AY register')
            seen.add(register)
            if register in PERIOD_LOW_REGISTERS:
                output[at+1]=(value+previous[register] if decode else value-previous[register])&255
            previous[register]=output[at+1] if decode else value
        result.append(bytes(output))
    return result


def huffman_bytes(data):
    if data[:4]!=b'AYD1':raise ValueError('expected AYD1')
    return b'AYH1'+data[4:]


def encode(records,initial):
    coded,metadata=ay_huffman_stream.encode(transform(records,initial),initial)
    return b'AYD1'+coded[4:],dict(metadata,wire='AYD1',period_delta_registers=list(PERIOD_LOW_REGISTERS),
        lossless=True,original_tick_records_preserved=True)


def decode(data):
    initial,records=ay_huffman_stream.decode(huffman_bytes(data))
    return initial,transform(records,initial,decode=True)
