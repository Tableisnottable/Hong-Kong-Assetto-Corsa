"""Decode every mip of the prepared full-loop BC1 source textures."""
from pathlib import Path
import sys,json,hashlib,struct,io,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image

def main():
    full=ROOT/'driving_test/route_scenery';manifest=full/'prepared_manifest.json';prepared=json.loads(manifest.read_text(encoding='utf-8'))
    errors=[];levels=0;total=0;chain_hash=hashlib.sha256()
    for item in sorted(prepared['materials'],key=lambda m:m['texture']):
        path=full/'textures'/item['texture'];raw=path.read_bytes();header=bytearray(raw[:128])
        chain_hash.update(item['texture'].encode());chain_hash.update(hashlib.sha256(raw).digest())
        try:
            if raw[:4]!=b'DDS ' or raw[84:88]!=b'DXT1':raise ValueError('Expected legacy BC1 DDS')
            h,w=struct.unpack_from('<II',header,12);count=struct.unpack_from('<I',header,28)[0]
            if [w,h]!=item['dimensions'] or count!=int(math.log2(max(w,h)))+1:raise ValueError('Unexpected dimensions/mip count')
            offset=128
            for level in range(count):
                n=((w+3)//4)*((h+3)//4)*8;payload=raw[offset:offset+n]
                if len(payload)!=n:raise ValueError('Truncated mip '+str(level))
                single=header.copy();struct.pack_into('<II',single,12,h,w);struct.pack_into('<I',single,20,n);struct.pack_into('<I',single,28,1);struct.pack_into('<I',single,108,0x1000)
                struct.pack_into('<I',single,8,struct.unpack_from('<I',single,8)[0]&~0x20000)
                with Image.open(io.BytesIO(single+payload)) as im:
                    im.load()
                    if im.size!=(w,h):raise ValueError('Decoded dimensions mismatch')
                levels+=1;offset+=n;w=max(1,w//2);h=max(1,h//2)
            if offset!=len(raw):raise ValueError('Trailing mip payload')
            total+=len(raw)-128
        except Exception as e:errors.append({'texture':item['texture'],'error':str(e)})
    report={'passed':not errors,'errors':errors,'texture_files':len(prepared['materials']),'mip_levels_decoded':levels,'unique_texture_gpu_payload_bytes':total,'prepared_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'ordered_texture_name_and_sha256_digest':chain_hash.hexdigest(),'scope':'Prepared source texture data only; in-game appearance and VRAM untested'}
    (full/'reports').mkdir(exist_ok=True);(full/'reports/all_mip_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
