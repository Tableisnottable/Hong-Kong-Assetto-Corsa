"""Fetch only the public LandsD sheets needed for the 3.445 km test loop."""
from pathlib import Path
import sys,json,urllib.request,urllib.parse,hashlib,zipfile,concurrent.futures,time,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np
from shapely.geometry import LineString,Polygon
SOURCE=ROOT/'source/csdi_individualised';SOURCE.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'driving_test/route_scenery';OUT.mkdir(exist_ok=True)
SERVICE='https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1671676915450_88604/FeatureServer/0/query'

def fetch_sheet(item):
    sheet=item['sheet'];path=SOURCE/(sheet+'_GLTF.zip');partial=path.with_suffix('.partial')
    if not path.is_file():
        url=item['download_url'];attempt=0
        while True:
            try:
                start=partial.stat().st_size if partial.exists() else 0
                headers={'Range':f'bytes={start}-'} if start else {}
                req=urllib.request.Request(url,headers=headers)
                with urllib.request.urlopen(req,timeout=120) as response:
                    if start and response.status!=206:raise RuntimeError('Resume not honoured')
                    total=int(response.headers.get('Content-Length',0))+start;n=start;last=time.monotonic()
                    with partial.open('ab' if start else 'wb') as file:
                        while block:=response.read(1024*1024):
                            file.write(block);n+=len(block)
                            if time.monotonic()-last>20:print('DOWNLOAD',sheet,n,total,flush=True);last=time.monotonic()
                if n!=total:raise RuntimeError('Short source download')
                partial.replace(path);break
            except Exception:
                attempt+=1
                if attempt>=3:raise
                print('RETRY',sheet,attempt,flush=True)
    destination=SOURCE/sheet;destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for entry in z.infolist():
            target=destination/entry.filename
            if not target.resolve().is_relative_to(destination.resolve()):raise RuntimeError('Unsafe source ZIP path')
            if entry.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            if target.is_file() and target.stat().st_size==entry.file_size:continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(entry) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
    with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    record={k:v for k,v in item.items() if k!='download_url'};record.update(archive_bytes=path.stat().st_size,archive_sha256=sha,source_glTF_files=len(list(destination.rglob('*.gltf'))))
    (OUT/(sheet+'_source.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('SOURCE_READY',sheet,record['archive_bytes'],record['source_glTF_files'],flush=True);return record

def main():
    route=np.load(ROOT/'driving_test/route_geometry.npz')['center']
    origin=np.array([826000.,833000.]);line=LineString(route[:,:2]+origin);area=line.buffer(160)
    lo=line.bounds;query={'f':'json','where':'1=1','geometry':','.join(str(x) for x in [lo[0]-200,lo[1]-200,lo[2]+200,lo[3]+200]),'geometryType':'esriGeometryEnvelope','inSR':2326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','returnGeometry':'true','outSR':2326}
    with urllib.request.urlopen(SERVICE+'?'+urllib.parse.urlencode(query),timeout=60) as response:j=json.load(response)
    selected=[]
    for feature in j['features']:
        poly=Polygon(feature['geometry']['rings'][0])
        if not poly.intersects(area):continue
        a=feature['attributes'];url=a['Format_glTF']
        if urllib.parse.urlparse(url).hostname!='download.map.gov.hk':raise RuntimeError('Unexpected source host')
        selected.append({'sheet':a['SHEETNO'],'bounds_epsg2326':[round(x) for x in poly.bounds],'revision_epoch_ms':a['REVISIONDATE'],'download_url':url,'route_length_within_sheet_m':line.intersection(poly).length})
    # Process core route sheets first; at most two download streams share bandwidth.
    selected.sort(key=lambda x:(x['route_length_within_sheet_m']<=0,x['sheet']))
    print('SELECTED_SHEETS',[x['sheet'] for x in selected],flush=True)
    report={'route_length_m':line.length,'scenery_buffer_m':160,'sheets':[]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for rec in pool.map(fetch_sheet,selected):
            report['sheets'].append(rec);(OUT/'source_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ALL_ROUTE_SOURCES_READY',len(report['sheets']),flush=True)

if __name__=='__main__':main()
