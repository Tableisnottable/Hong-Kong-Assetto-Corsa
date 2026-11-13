"""Fetch a small pinned CC0 texture library from the official Poly Haven API."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'source/finish_library';OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'HK1to1LocalAuthoring/0.5 (small texture-library request)'}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=90) as r:return r.read()
def main():
    license_bytes=fetch('https://polyhaven.com/license')
    if b'CC0' not in license_bytes:raise RuntimeError('Official license page did not identify CC0; review before use')
    (OUT/'polyhaven_license_snapshot.html').write_bytes(license_bytes)
    choices={'tree_small_02':{'leaves_diff':('1k','png'),'leaves_alpha':('1k','png'),'branch_diff':('1k','png')},'island_tree_01':{'leaves_diff':('1k','png'),'leaves_alpha':('1k','png'),'branches_diff':('1k','png')},'asphalt_02':{'Diffuse':('2k','jpg')},'forest_ground_04':{'Diffuse':('2k','jpg')},'aerial_grass_rock':{'Diffuse':('2k','jpg')}}
    manifest={'source':'Poly Haven official API/download CDN','license':'CC0; official page retained for review','license_url':'https://polyhaven.com/license','retrieved_local_date':'2026-11-14','assets':[]}
    for asset,maps in choices.items():
        info=json.loads(fetch('https://api.polyhaven.com/info/'+asset));files=json.loads(fetch('https://api.polyhaven.com/files/'+asset));folder=OUT/asset;folder.mkdir(exist_ok=True)
        (folder/'asset_info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
        record={'id':asset,'name':info.get('name'),'authors':info.get('authors'),'dimensions_mm':info.get('dimensions'),'asset_page':'https://polyhaven.com/a/'+asset,'files':[]}
        for kind,(resolution,fmt) in maps.items():
            item=files[kind][resolution][fmt];name=item['url'].rsplit('/',1)[1];path=folder/name
            payload=path.read_bytes() if path.is_file() else fetch(item['url'])
            if len(payload)!=item['size'] or hashlib.md5(payload).hexdigest()!=item['md5']:raise RuntimeError('Download checksum mismatch: '+name)
            path.write_bytes(payload);record['files'].append({'map':kind,'file':str(path.relative_to(OUT)).replace('\\','/'),'url':item['url'],'bytes':len(payload),'md5':item['md5'],'sha256':hashlib.sha256(payload).hexdigest()})
        manifest['assets'].append(record);print(asset,sum(f['bytes'] for f in record['files']),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
