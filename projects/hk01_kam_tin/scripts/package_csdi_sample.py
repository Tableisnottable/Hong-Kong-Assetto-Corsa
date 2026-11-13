"""Package the validated scenery sample and optionally update its owned install."""
from pathlib import Path
import argparse,json,hashlib,shutil,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image,ImageDraw,ImageFont
TRACK='hk01_kam_tin_test';SAMPLE=ROOT/'driving_test/csdi_sample';REPORTS=SAMPLE/'reports'
PACKAGE=ROOT/'release_csdi_sample/content/tracks'/TRACK
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install-root',type=Path);args=parser.parse_args()
    binary=json.loads((REPORTS/'kn5_external_verification.json').read_text(encoding='utf-8'))
    scenery=json.loads((REPORTS/'scenery_external_verification.json').read_text(encoding='utf-8'))
    kn5=PACKAGE/(TRACK+'.kn5');sha=digest(kn5)
    if not binary['passed'] or not scenery['passed']:raise RuntimeError('Validation failed')
    if binary['kn5_sha256']!=sha or scenery['new_kn5_sha256']!=sha:raise RuntimeError('Validation is stale')
    base=ROOT/'release/content/tracks'/TRACK
    for part in ['data','sources']:
        shutil.copytree(base/part,PACKAGE/part,dirs_exist_ok=True)
    for file in ['models.ini','map.png']:shutil.copy2(base/file,PACKAGE/file)
    (PACKAGE/'ui').mkdir(exist_ok=True)
    ui=json.loads((base/'ui/ui_track.json').read_text(encoding='utf-8'))
    ui['version']='0.2-csdi-sample'
    ui['description']='3.445 km solo test loop. Version 0.2 adds adapted real Lands Department scenery on one 750 x 600 m tile (6-NE-12D). Other areas remain blockout. Temporary 7 m road and original collision/spawns retained. No AI. Game loading and FPS await user test. Map from Lands Department; source data © Government of the Hong Kong SAR, https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.'
    (PACKAGE/'ui/ui_track.json').write_text(json.dumps(ui,indent=2,ensure_ascii=False),encoding='utf-8')
    image=Image.open(REPORTS/'csdi_sample_overview.png').convert('RGB');image=image.resize((1024,640));d=ImageDraw.Draw(image)
    d.rectangle((0,0,1024,85),fill=(17,37,39));d.text((22,8),'KAM TIN / REAL SCENERY TEST 0.2',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',30),fill='white')
    d.text((24,49),'3.445 KM LOOP  |  REAL SCENERY ON ONE 750 x 600 m TILE',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19),fill=(190,230,212))
    d.rectangle((0,591,1024,640),fill=(245,245,245))
    with Image.open(ROOT/'source/csdi_individualised/landsd_logo_fb.jpg') as logo:
        logo=logo.convert('RGB');logo.thumbnail((43,43));image.paste(logo,(10,594))
    d.text((65,595),'Map from Lands Department | © Government of the Hong Kong SAR',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17),fill=(15,35,35))
    d.text((65,617),'3d.map.gov.hk  |  Road reference © OpenStreetMap contributors',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14),fill=(15,35,35))
    image.save(PACKAGE/'ui/preview.png');image.save(PACKAGE/'ui/preview.jpg',quality=90)
    shutil.copy2(PACKAGE/'map.png',PACKAGE/'ui/outline.png');shutil.copy2(ROOT/'ATTRIBUTION.md',PACKAGE/'ATTRIBUTION.md')
    terms=ROOT/'source/csdi_individualised/TERMS_SNAPSHOT_2026-11-13.txt'
    if not terms.is_file():terms=ROOT/'docs/LandsD_terms_snapshot.txt'
    shutil.copy2(terms,PACKAGE/'sources/LandsD_terms_snapshot.txt')
    prep=json.loads((SAMPLE/'prepared_manifest.json').read_text(encoding='utf-8'))
    source={k:prep[k] for k in ['dataset','sheet','coverage_epsg2326','source_archive_bytes','source_archive_sha256','sheet_revision','origin_epsg2326','metres_per_unit','removed_triangles','missing_source_textures','scenery_role','road_exclusion_buffer_m']}
    source['website']='https://3d.map.gov.hk/';source['dataset_id']='landsd_rcd_1671676915450_88604';source['retrieved']='2026-11-13'
    (PACKAGE/'sources/csdi_sample.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    readme='''HONG KONG — KAM TIN DRIVING TEST 0.2 / CSDI SCENERY SAMPLE

Select Hong Kong — Kam Tin Driving Test.
Use Practice, one player car, no AI opponents, clear daytime. Start from pits.
Follow the continuous paved 3.445 km loop. Use Return to pits if needed.

Version 0.2 adds real Lands Department textured models on source tile
6-NE-12D (750 x 600 metres), not along the entire route. Outside that tile,
the region remains a simplified blockout. Photogrammetry can be rough up
close; incomplete surfaces, terrain transitions and neutral fallback texture
on one source building remain. Nearby roads are not drivable in this test.

The road retains its temporary 7 m width, smoothed profile, pit apron and
synthetic safety barriers. All 272 physical mesh vertex/index payloads and
all spawn/timing matrices match version 0.1. Visual terrain was blended near
the road and tile boundary. Imported scenery has no vehicle collision.

Independent KN5 checks passed: geometry, indices, source texture decoding,
and a protected corridor around the road. Actual game loading, driving and
FPS have NOT been tested. Please test these yourself and report load errors,
spawn problems, holes, barrier snagging, missing textures and frame rate.

Map from Lands Department. Source data © Government of the Hong Kong SAR.
https://3d.map.gov.hk/
Road reference © OpenStreetMap contributors. https://www.openstreetmap.org/copyright
See ATTRIBUTION.md and sources/LandsD_terms_snapshot.txt for source conditions.
'''
    (PACKAGE/'TEST_README.txt').write_text(readme,encoding='utf-8')
    files={str(p.relative_to(PACKAGE)).replace('\\','/'):p for p in PACKAGE.rglob('*') if p.is_file() and p.name!='manifest.json'}
    manifest={rel:{'bytes':p.stat().st_size,'sha256':digest(p)} for rel,p in sorted(files.items())}
    (PACKAGE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=ROOT.parent/'HK_KamTin_Driving_Test_v0.2_CSDI.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(PACKAGE.rglob('*')):
            if p.is_file():z.write(p,'content/tracks/'+TRACK+'/'+str(p.relative_to(PACKAGE)).replace('\\','/'))
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP CRC failed: '+bad)
    report={'passed':True,'version':ui['version'],'track_id':TRACK,'kn5_sha256':sha,'archive':str(archive.resolve()),'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive),'package_files':len(manifest)+1,'game_loading_driving_fps':'not tested; user will test','installed_to':None}
    if args.install_root:
        ac=args.install_root.resolve();destination=ac/'content/tracks'/TRACK
        if not (ac/'acs.exe').is_file():raise RuntimeError('Not an AC install')
        if destination.exists():
            if not (destination/'manifest.json').is_file():raise RuntimeError('Existing track has no owned manifest')
            old=json.loads((destination/'manifest.json').read_text(encoding='utf-8'))
            actual={str(p.relative_to(destination)).replace('\\','/') for p in destination.rglob('*') if p.is_file()}
            if actual!=set(old)|{'manifest.json'}:raise RuntimeError('Installed files differ: preserve user edits')
            if set(old)-set(manifest):raise RuntimeError('Update would leave stale old files')
            for rel,info in old.items():
                if digest(destination/rel)!=info['sha256']:raise RuntimeError('Installed file edited: '+rel)
        shutil.copytree(PACKAGE,destination,dirs_exist_ok=True)
        for rel,info in manifest.items():
            if digest(destination/rel)!=info['sha256']:raise RuntimeError('Installed verification failed: '+rel)
        if json.loads((destination/'manifest.json').read_text(encoding='utf-8'))!=manifest:raise RuntimeError('Manifest mismatch')
        report['installed_to']=str(destination);report['installed_file_hashes_verified']=True
    (REPORTS/'package_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
