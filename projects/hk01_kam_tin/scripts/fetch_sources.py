"""Fetch source data locally; downloads and API responses must stay out of Git."""
from pathlib import Path
import argparse,json,urllib.request,urllib.parse,hashlib,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1]
SERVICE='https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1671676915450_88604/FeatureServer/0/query'
FOUNDATION={
    'hong-kong-latest.osm.pbf':'https://download.geofabrik.de/asia/china/hong-kong-latest.osm.pbf',
    'hong-kong-boundary-913110.osm':'https://api.openstreetmap.org/api/0.6/relation/913110/full',
    'Whole_HK_DTM_5m.zip':'https://www.landsd.gov.hk/landsd_psi_data/SMO/data/Whole_HK_DTM_5m.zip'}

def download(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():print('Retaining existing source:',path.name);return
    temp=path.with_suffix(path.suffix+'.partial')
    with urllib.request.urlopen(url,timeout=120) as response,temp.open('wb') as out:
        shutil.copyfileobj(response,out,1024*1024)
    temp.replace(path)
    with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    print(path.name,path.stat().st_size,'bytes SHA256',sha)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--foundation',action='store_true');p.add_argument('--sheet',default=None);a=p.parse_args()
    if not a.foundation and not a.sheet:p.error('Choose --foundation and/or --sheet 6-NE-12D')
    if a.foundation:
        for name,url in FOUNDATION.items():download(url,ROOT/'source'/name)
    if a.sheet:
        # Sheet names come from the public LandsD index. Restrict query syntax.
        if not a.sheet.replace('-','').isalnum():raise ValueError('Invalid sheet number')
        params={'f':'json','where':"SHEETNO='"+a.sheet+"'",'outFields':'SHEETNO,REVISIONDATE,Format_glTF','returnGeometry':'false'}
        with urllib.request.urlopen(SERVICE+'?'+urllib.parse.urlencode(params),timeout=60) as response:j=json.load(response)
        features=j.get('features',[])
        if len(features)!=1:raise RuntimeError('Expected one downloadable sheet in the government index')
        url=features[0]['attributes']['Format_glTF']
        if urllib.parse.urlparse(url).hostname!='download.map.gov.hk':raise RuntimeError('Unexpected model download host')
        path=ROOT/'source/csdi_individualised'/(a.sheet+'_GLTF.zip');download(url,path)
        destination=path.parent/a.sheet;destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(path) as z:
            for item in z.infolist():
                if not (destination/item.filename).resolve().is_relative_to(destination.resolve()):raise RuntimeError('Unsafe archive path')
            z.extractall(destination)
        # Official assets are used only for attribution in the test-start board.
        for name in ['landsd_logo.svg','landsd_logo_fb.jpg']:
            download('https://www.landsd.gov.hk/images/'+name,path.parent/name)
        print('Extracted sheet',a.sheet,'under local ignored source directory')
    print('New downloads may differ from the recorded November 2026 snapshots; inspect hashes before rebuilding.')

if __name__=='__main__':main()
