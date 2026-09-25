import struct, sys
f = open(sys.argv[1], 'rb')
def rd(fmt): return struct.unpack('<'+fmt, f.read(struct.calcsize('<'+fmt)))[0]
def rstr(): n = rd('Q'); return f.read(n).decode('utf-8', 'replace')
SC = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
def val(t):
    if t in SC: return rd(SC[t])
    if t == 8: return rstr()
    if t == 9:
        et = rd('I'); n = rd('Q')
        items = [val(et) for _ in range(n)]
        return items
assert f.read(4) == b'GGUF'
ver = rd('I'); nt = rd('Q'); nkv = rd('Q')
print('tensors', nt)
for _ in range(nkv):
    k = rstr(); t = rd('I'); v = val(t)
    if k.startswith('tokenizer.ggml.') and k != 'tokenizer.ggml.model': continue
    if 'chat_template' in k: continue
    s = str(v) if not isinstance(v, list) else (str(v[:64]) + (f' ...({len(v)})' if len(v) > 64 else ''))
    print(k, '=', s[:300])
types = {}
for _ in range(nt):
    name = rstr(); nd = rd('I'); dims = [rd('Q') for _ in range(nd)]; tt = rd('I'); off = rd('Q')
    kind = 'exps' if '_exps' in name else 'other'
    types.setdefault((kind, tt), 0); types[(kind, tt)] += 1
print('tensor types (kind, ggml_type): count', types)
