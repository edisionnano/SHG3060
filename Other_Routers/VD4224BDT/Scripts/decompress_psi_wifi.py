import sys

data = open(sys.argv[1], 'rb').read()
data_start = data.index(b'>', data.index(b'<crc=')) + 1
while data[data_start] == 0:
    data_start += 1
compressed = data[data_start:]

table = [bytes([i]) for i in range(256)] + [None, None]
next_code = 258
bits = 9
bit_buf = bit_count = pos = 0
output = bytearray()
prev = None

while True:
    while bit_count < bits and pos < len(compressed):
        bit_buf = (bit_buf << 8) | compressed[pos]
        bit_count += 8
        pos += 1
    if bit_count < bits:
        break
    bit_count -= bits
    sym = (bit_buf >> bit_count) & ((1 << bits) - 1)

    if sym == 257:
        break
    if sym == 256:
        table = [bytes([i]) for i in range(256)] + [None, None]
        next_code, bits, prev = 258, 9, None
        continue

    entry = table[sym] if sym < next_code else prev + prev[:1]
    output.extend(entry)

    if prev is not None:
        table.append(prev + entry[:1])
        next_code += 1
        if next_code == (1 << bits) - 1 and bits < 12:
            bits += 1

    prev = entry

result = bytes(output).rstrip(b'\x00')
if len(sys.argv) > 2:
    open(sys.argv[2], 'wb').write(result)
else:
    sys.stdout.buffer.write(result)
