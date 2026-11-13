"""Package the inspected v0.4 visual pass; install only an unchanged owned track."""
from pathlib import Path
import argparse,configparser,hashlib,json,os,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image,ImageDraw,ImageFont
TRACK='hk01_kam_tin_test';VERSION='0.4-quality-pass'
Q=ROOT/'driving_test/quality_pass';REPORTS=Q/'reports'
PACKAGE=ROOT/'release_quality_v04/content/tracks'/TRACK
OLD=ROOT/'release_route_scenery/content/tracks'/TRACK

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def assert_manifest(folder,manifest):
    files={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if files!=set(manifest)|{'manifest.json'}:raise RuntimeError('Unexpected files; preserve additions: '+str(folder))
    for rel,info in manifest.items():
        if (folder/rel).stat().st_size!=info['bytes'] or digest(folder/rel)!=info['sha256']:
            raise RuntimeError('File changed; do not overwrite: '+str(folder/rel))

def main():
    p=argparse.ArgumentParser();p.add_argument('--install-root',type=Path);args=p.parse_args()
    check=json.loads((REPORTS/'model_verification.json').read_text(encoding='utf-8'))
    independent=json.loads((REPORTS/'base_independent_verification.json').read_text(encoding='utf-8'))
    visual=json.loads((REPORTS/'visual_review.json').read_text(encoding='utf-8'))
    surface=json.loads((ROOT/'driving_test/route_scenery/reports/route_surface_verification.json').read_text(encoding='utf-8'))
    mip=json.loads((ROOT/'driving_test/route_scenery/reports/all_mip_verification.json').read_text(encoding='utf-8'))
    if not all([check['passed'],check['physical_meshes_unchanged'],check['spawn_timing_nodes_unchanged'],surface['passed'],mip['passed'],visual['geometry_review_passed']]):
        raise RuntimeError('Required validation missing or failed')
    if not independent['passed'] or independent['kn5_sha256']!=digest(PACKAGE/(TRACK+'.kn5')):raise RuntimeError('Independent base-model check failed or stale')
    for view in visual['views']:
        if digest(REPORTS/view['file'])!=view['sha256']:raise RuntimeError('Visual review is stale')
    if visual['quality_build_sha256']!=digest(REPORTS/'quality_build.json'):raise RuntimeError('Visual review is for a different build')
    if check['total_texture_gpu_payload_bytes']>2*1024**3:raise RuntimeError('Texture budget exceeded')
    ini=configparser.ConfigParser();ini.read(PACKAGE/'models.ini')
    names={ini[s]['FILE'] for s in ini.sections()}
    if names!={m['filename'] for m in check['models']}:raise RuntimeError('Model list mismatch')
    for model in check['models']:
        if digest(PACKAGE/model['filename'])!=model['kn5_sha256']:raise RuntimeError('Model report is stale')
        audit=model['material_audit']
        if audit['missing_explicit_emissive'] or audit['nonzero_emissive']:raise RuntimeError('Material emissive audit failed')
    # Preserve the previous release as a separate, unchanged local rollback.
    old_manifest=json.loads((OLD/'manifest.json').read_text(encoding='utf-8'));assert_manifest(OLD,old_manifest)
    for rel in old_manifest:
        if Path(rel).suffix=='.kn5' or rel=='models.ini':continue
        target=PACKAGE/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OLD/rel,target)
    ui=json.loads((PACKAGE/'ui/ui_track.json').read_text(encoding='utf-8'))
    ui['version']=VERSION
    ui['description']='3.445 km Kam Tin solo driving test, v0.4 visual repair. Raised generic photomesh and source vegetation replaced by authored trees at inferred canopy locations. Retained individualised buildings and infrastructure. Matte road and track materials, explicit zero emissive. Temporary road/profile and barriers; eight blue test markers. Practice, one car, clear daytime. User confirmed v0.3 loading/driving; v0.4 appearance and FPS need a fresh user test. Map from Lands Department; source data © Government of the Hong Kong SAR, https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.'
    (PACKAGE/'ui/ui_track.json').write_text(json.dumps(ui,indent=2,ensure_ascii=False),encoding='utf-8')
    with Image.open(REPORTS/'checkpoint_01.png') as src:im=src.convert('RGB').resize((1024,640))
    draw=ImageDraw.Draw(im);font='C:/Windows/Fonts/segoeui.ttf'
    draw.rectangle((0,0,1024,80),fill=(20,37,32));draw.text((22,7),'KAM TIN / VISUAL REPAIR 0.4',font=ImageFont.truetype(font,30),fill='white')
    draw.text((24,46),'3.445 KM | SOLO TEST | BLENDER PREVIEW',font=ImageFont.truetype(font,19),fill=(200,222,203))
    draw.rectangle((0,586,1024,640),fill=(245,245,245))
    with Image.open(ROOT/'source/csdi_individualised/landsd_logo_fb.jpg') as logo:
        logo=logo.convert('RGB');logo.thumbnail((43,43));im.paste(logo,(9,592))
    draw.text((65,591),'Map from Lands Department | © Government of the Hong Kong SAR',font=ImageFont.truetype(font,17),fill=(20,45,35))
    draw.text((65,616),'3d.map.gov.hk | Roads © OpenStreetMap contributors',font=ImageFont.truetype(font,15),fill=(20,45,35))
    im.save(PACKAGE/'ui/preview.png');im.save(PACKAGE/'ui/preview.jpg',quality=90)
    shutil.copy2(ROOT/'ATTRIBUTION.md',PACKAGE/'ATTRIBUTION.md')
    adaptation=['raised generic photomesh and source vegetation removed','retained GENERIC photo ground projected onto visual terrain to remove jagged stumps; its imagery is still source-derived','authored 3D trees at inferred source canopy positions; not surveyed species or individually measured trees','track-local matte surface textures and reduced lighting multipliers','all exported materials explicitly zero emissive','original physical geometry and spawn/timing matrices retained']
    for name in ['csdi_sample.json','route_scenery.json']:
        path=PACKAGE/'sources'/name;j=json.loads(path.read_text(encoding='utf-8'));j['version']=VERSION;j['adaptations']+=adaptation;path.write_text(json.dumps(j,indent=2,ensure_ascii=False),encoding='utf-8')
    testing='''KAM TIN — VISUAL REPAIR 0.4

READY FOR YOUR OWN COMPARISON TEST
Select Hong Kong — Kam Tin Driving Test (hk01_kam_tin_test).
Use Practice, one car, no opponents, clear daytime, start from pits.
Keep the same car, weather/time and graphics settings as your previous screenshot.

1. Leave the pit apron, keep left and drive the complete 3.445 km loop.
2. Follow the blue TEST POINT markers 1–8 and return to point 1.
3. Compare road/ground brightness and the new tree silhouettes at the same location.
4. Check both lanes, barrier edges and Return to pits as before.
5. Send a new screenshot and the nearest checkpoint if a surface is still white,
   foliage looks wrong, scenery is missing or you encounter a driving defect.
6. Record minimum FPS during a complete lap; one screenshot is not a benchmark.

WHAT CHANGED
Removed source vegetation and raised GENERIC photomesh fragments. Projected the
remaining GENERIC photo ground onto visual terrain to remove jagged stumps. Added authored
3D trees at canopy locations inferred from source geometry/texture. Retained the
individualised buildings, infrastructure and terrain. Added restrained asphalt,
concrete, grass and paint textures. Lowered track-local material multipliers and
explicitly set emissive to zero. Collision geometry and spawn/timing are unchanged.

LIMITS
This remains a provisional test route, not finished real-world quality or all
Hong Kong. Tree species, exact positions and heights are not surveyed. Removing
raised GENERIC data also removes some non-individualised structures. Residual
ground photomesh, generic tree shapes, temporary road width/profile, junctions
and safety barriers still need manual production work. Source scenery is visual
only; the original road and barriers provide vehicle collision. Neighbouring
roads are scenery. No AI traffic, rain/night tuning or multiplayer validation.

The user confirmed loading/driving in v0.3 but rejected its appearance. Version
0.4 passed the recorded binary, texture, corridor and baseline-physics checks.
Blender renders check geometry only; they do not prove Assetto Corsa lighting.
Version 0.4 engine appearance, driving and FPS await your comparison test.
The game was not launched automatically. Global graphics/CSP settings are unchanged.

Map from Lands Department. Source data © Government of the Hong Kong SAR.
https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.
See ATTRIBUTION.md and sources/LandsD_terms_snapshot.txt.
'''
    for name in ['TEST_README.txt','TESTING.txt']:(PACKAGE/name).write_text(testing,encoding='utf-8')
    (ROOT/'TESTING.md').write_text(testing,encoding='utf-8')
    files={p.relative_to(PACKAGE).as_posix():p for p in PACKAGE.rglob('*') if p.is_file() and p.name!='manifest.json'}
    manifest={rel:{'bytes':f.stat().st_size,'sha256':digest(f)} for rel,f in sorted(files.items())}
    (PACKAGE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');assert_manifest(PACKAGE,manifest)
    archive=ROOT.parent/'HK_KamTin_Quality_Test_v0.4.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
        for rel,f in sorted(files.items()):z.write(f,'content/tracks/'+TRACK+'/'+rel)
        z.write(PACKAGE/'manifest.json','content/tracks/'+TRACK+'/manifest.json')
    with zipfile.ZipFile(archive) as z:
        expected={'content/tracks/'+TRACK+'/'+rel for rel in manifest}|{'content/tracks/'+TRACK+'/manifest.json'}
        if set(z.namelist())!=expected or z.testzip():raise RuntimeError('Archive contents/CRC failed')
    report={'passed':True,'version':VERSION,'track_id':TRACK,'file_count':len(manifest)+1,'model_files':len(names),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive),'installed_to':None,'installed_file_hashes_verified':False,'engine_test_v04':'pending user; no automatic game launch'}
    if args.install_root:
        ac=args.install_root.resolve();dest=ac/'content/tracks'/TRACK
        if not (ac/'acs.exe').is_file():raise RuntimeError('Invalid Assetto Corsa installation')
        if os.name=='nt' and '"acs.exe"' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq acs.exe','/FO','CSV','/NH'],text=True).lower():raise RuntimeError('Close the running game before updating its track')
        if dest.exists():
            if not (dest/'manifest.json').is_file():raise RuntimeError('Target is not an owned install')
            previous=json.loads((dest/'manifest.json').read_text(encoding='utf-8'));assert_manifest(dest,previous)
            if set(previous)-set(manifest):raise RuntimeError('Update leaves obsolete files; review explicitly')
        shutil.copytree(PACKAGE,dest,dirs_exist_ok=True);assert_manifest(dest,manifest)
        if json.loads((dest/'manifest.json').read_text(encoding='utf-8'))!=manifest:raise RuntimeError('Installed manifest mismatch')
        report['installed_to']=str(dest);report['installed_file_hashes_verified']=True
    (REPORTS/'package_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
