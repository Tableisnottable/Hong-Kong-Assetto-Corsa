"""Package the inspected v0.5 visual pass; install only an unchanged owned track."""
from pathlib import Path
import argparse,configparser,hashlib,json,os,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image,ImageDraw,ImageFont
TRACK='hk01_kam_tin_test';VERSION='0.5-reference-pass'
Q=ROOT/'driving_test/finish_pass';REPORTS=Q/'reports'
PACKAGE=ROOT/'release_finish_v05/content/tracks'/TRACK
OLD=ROOT/'release_quality_v04/content/tracks'/TRACK

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
    ui['description']='3.445 km Kam Tin solo test, v0.5 reference-informed visual pass. Route Twisk RWE/Repack is the quality target, not an achieved quality claim. New alpha-cut foliage, photographed asphalt/ground textures and authored W-beam safety rails/posts/reflectors. Reference assets were inspected read-only, not copied. Original driving/collision payloads and spawns retained; coarse test-wall collision remains behind visual rails. Road/junction widths, kerbs and roadside fidelity remain provisional. Daytime Practice, one car, no AI. Engine appearance/FPS await the user. Map from Lands Department; source data © Government of the Hong Kong SAR, https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors. Additional textures: Poly Haven CC0.'
    (PACKAGE/'ui/ui_track.json').write_text(json.dumps(ui,indent=2,ensure_ascii=False),encoding='utf-8')
    with Image.open(REPORTS/'checkpoint_01.png') as src:im=src.convert('RGB').resize((1024,640))
    draw=ImageDraw.Draw(im);font='C:/Windows/Fonts/segoeui.ttf'
    draw.rectangle((0,0,1024,80),fill=(20,37,32));draw.text((22,7),'KAM TIN / REFERENCE PASS 0.5',font=ImageFont.truetype(font,30),fill='white')
    draw.text((24,46),'3.445 KM | SOLO TEST | BLENDER PREVIEW',font=ImageFont.truetype(font,19),fill=(200,222,203))
    draw.rectangle((0,586,1024,640),fill=(245,245,245))
    with Image.open(ROOT/'source/csdi_individualised/landsd_logo_fb.jpg') as logo:
        logo=logo.convert('RGB');logo.thumbnail((43,43));im.paste(logo,(9,592))
    draw.text((65,591),'Map from Lands Department | © Government of the Hong Kong SAR',font=ImageFont.truetype(font,17),fill=(20,45,35))
    draw.text((65,616),'3d.map.gov.hk | Roads © OpenStreetMap contributors',font=ImageFont.truetype(font,15),fill=(20,45,35))
    im.save(PACKAGE/'ui/preview.png');im.save(PACKAGE/'ui/preview.jpg',quality=90)
    shutil.copy2(ROOT/'ATTRIBUTION.md',PACKAGE/'ATTRIBUTION.md')
    shutil.copy2(ROOT/'source/finish_library/manifest.json',PACKAGE/'sources/finish_assets.json')
    adaptation=['reference benchmark: installed Route Twisk RWE/Repack, read-only; no reference assets copied','Poly Haven CC0 texture adaptation with pinned checksum manifest','newly composed cutout foliage sprays and eight authored tree-shape variants','photographed asphalt and generic grass/rock fallback ground; not georeferenced Hong Kong imagery','authored folded steel safety rails, posts, bolts and reflectors following provisional test bounds','original physical mesh payloads and spawns retained; coarse wall collision remains behind visual rails']
    for name in ['csdi_sample.json','route_scenery.json']:
        path=PACKAGE/'sources'/name;j=json.loads(path.read_text(encoding='utf-8'));j['version']=VERSION;j['adaptations']+=adaptation;path.write_text(json.dumps(j,indent=2,ensure_ascii=False),encoding='utf-8')
    testing='''KAM TIN — REFERENCE-INFORMED TEST 0.5

QUALITY TARGET: ROUTE TWISK RWE / REPACK TEST
This is the next comparison build. It has NOT reached or been accepted at that
quality standard. The installed reference tracks are unchanged; their assets
are not copied into Kam Tin.

Select Hong Kong — Kam Tin Driving Test (hk01_kam_tin_test).
Use Practice, one car, no opponents, clear daytime, start from pits.
Restart the session to reload changed KN5 models. Keep your previous car,
time/weather and graphics settings for a fair brightness comparison.

1. Drive the complete 3.445 km loop, keeping left, past blue test points 1–8.
2. Inspect asphalt grain/cracks, paint edges and the new steel rail details.
3. Check leaf cutouts up close, tree silhouettes and foliage performance.
4. Check both lanes, the pit entry, safety barriers and Return to pits.
5. Report a screenshot and nearest test point for missing textures, bright
   surfaces, scenery holes or driving defects. Record minimum FPS over a lap.

CHANGES
Photographed asphalt and ground textures; worn alpha-cut paint; new composed
foliage-spray textures, eight tree-shape variants and bark texture; smoother
visual terrain; folded W-beam visual safety rails, posts, bolts and reflectors.
Original individualised CSDI buildings/infrastructure and full-loop layout remain.

UNFINISHED
The road/profile/junctions are still provisional. Kerbs, drainage, proper local
barrier/fence placement, varied region-appropriate vegetation, bespoke roadside
assets, improved close-up building facades and scenery-ground seams still need
production work. Some GENERIC source structures were removed in v0.4; source
ground is flattened photo scenery. New foliage is generic, not surveyed species.
The rail positions follow test safety bounds, not a real guardrail survey.
Original coarse wall collision remains behind the new visual rails. It must be
replaced together with proper roadside/collision modelling in a later pass.
Neighbouring roads are scenery. This is not all Hong Kong or the full region.
No AI traffic, rain/night tuning or multiplayer validation is included.

CHECKS
Binary/texture and alpha-cut material checks, baseline physics/spawn comparison,
road/pit clearance checks, Blender geometry review, ZIP CRC and installed hashes
are recorded. Retained road support is unchanged from the previous surface test.
These checks do not prove engine lighting, driving behaviour or FPS. The user
loaded/drove v0.3 but rejected its appearance; v0.5 needs a fresh comparison.
No automatic game launch or global graphics/CSP change is performed.

Map from Lands Department. Source data © Government of the Hong Kong SAR.
https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.
Additional texture sources: Poly Haven, CC0. See ATTRIBUTION.md and the source
checksum manifest. Original source data and generated large assets stay local.
'''
    for name in ['TEST_README.txt','TESTING.txt']:(PACKAGE/name).write_text(testing,encoding='utf-8')
    (ROOT/'TESTING.md').write_text(testing,encoding='utf-8')
    files={p.relative_to(PACKAGE).as_posix():p for p in PACKAGE.rglob('*') if p.is_file() and p.name!='manifest.json'}
    manifest={rel:{'bytes':f.stat().st_size,'sha256':digest(f)} for rel,f in sorted(files.items())}
    (PACKAGE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');assert_manifest(PACKAGE,manifest)
    archive=ROOT.parent/'HK_KamTin_Reference_Test_v0.5.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
        for rel,f in sorted(files.items()):z.write(f,'content/tracks/'+TRACK+'/'+rel)
        z.write(PACKAGE/'manifest.json','content/tracks/'+TRACK+'/manifest.json')
    with zipfile.ZipFile(archive) as z:
        expected={'content/tracks/'+TRACK+'/'+rel for rel in manifest}|{'content/tracks/'+TRACK+'/manifest.json'}
        if set(z.namelist())!=expected or z.testzip():raise RuntimeError('Archive contents/CRC failed')
    report={'passed':True,'version':VERSION,'track_id':TRACK,'file_count':len(manifest)+1,'model_files':len(names),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive),'installed_to':None,'installed_file_hashes_verified':False,'engine_test_v05':'pending user; no automatic game launch'}
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
