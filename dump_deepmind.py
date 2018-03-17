"""
Copyright 2018 Oscillator Sink

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import mido
import pathlib
import base64
import json
from collections import OrderedDict

__version__ = "0.1"

BANKS = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7}

def print_ports():
    print("Inputs:")
    print("\n".join(mido.get_input_names()))
    print()
    print("Outputs:")
    print("\n".join(mido.get_output_names()))
    

def unpack_bytes(data):
    i = 0
    unpacked = []
    while True:
        chunk = data[i: i + 8]
        if not chunk:
            break
        if len(chunk) != 8:
            raise ValueError("non-8 length chunk when unpacking data")

        for j in range(1, 8):
            unpacked.append(chunk[j] | (chunk[0] & (1 << (j -1))))

        i += 8

    return bytes(unpacked)

def main(args):
    
    out_port_name = args[0]
    in_port_name = args[1]
    bank = BANKS[args[2].upper()]
    first_patch_no = int(args[3])
    last_patch_no = int(args[4])
    out_path = pathlib.Path(args[5])

    if first_patch_no < 0 or first_patch_no > 127:
        raise ValueError("First patch number must be between 0 and 127 inclusive")
    if last_patch_no < first_patch_no or last_patch_no > 127:
        raise ValueError("Last patch number must be between 0 and 127 inclusive and not less than First patch number")
    
    message_bytes = [
        0xf0,
        0x00, 0x20, 0x32,
        0x20,
        0x00,
        0x09,
        bank,
        first_patch_no,
        last_patch_no,
        0xf7
        ]

    out_port = mido.open_output(out_port_name)
    in_port = mido.open_input(in_port_name)

    message = mido.Message.from_bytes(message_bytes)

    out_port.send(message)
    patches = []
    while len(patches) < 1 + (last_patch_no - first_patch_no):
        sysex = in_port.poll()
        if sysex:
            patches.append(sysex)
            
    out_port.close()
    in_port.close()

    patches_for_output = OrderedDict()
    
    for patch in patches:
        # TODO: sense checks?
        p_data = bytes(patch.bytes())
        param_data_packed = p_data[10:-1]
        param_data_unpacked = unpack_bytes(param_data_packed)
        patch_name = param_data_unpacked[223:239].decode("ascii").rstrip("\0").rstrip()
        out_fname = f"""{"ABCDEFGH"[p_data[8]]}_{p_data[9] + 1:03}_{patch_name}.sysex"""

        b64_param_data = base64.b64encode(param_data_packed)

        patches_for_output[patch_name] = b64_param_data.decode("ascii")

        out = open(out_path / out_fname, "xb")
        out.write(p_data)
        out.close()

    out = open(out_path / "patch_lookup.json", "xt", encoding="utf8")
    json.dump(patches_for_output, out, indent="  ")
    out.close()
        
if __name__ == "__main__":
    if "-l" in sys.argv[1:]:
        print()
        print_ports()
        exit(0)
    if len(sys.argv) < 7:
        me = pathlib.Path(sys.argv[0]).name
        print()
        print(f"USAGE: {me} <output midi port> <input midi port> <bank A-H>")
        print( "             <first program no.> <last program no.> <output path>")
        print( "             [-l]")
        print()
        print("Dumps patches from a Behringer DeepMind synth for backup.")
        print()
        print("Input and output port names can be ascertained by using the -l switch")
        print("which will display all input and output switches and exit.")
        print("First and last program numbers are inclusive, and are zero indexed (ie")
        print("one less than is displayed on the synth.")
        print()
        exit(1)
    main(sys.argv[1:])
