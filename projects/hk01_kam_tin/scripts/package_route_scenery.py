"""Package the complete test loop after hash-bound model and surface checks."""
from pathlib import Path
import sys,json,argparse,hashlib,shutil,zipfile,configparser
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image,ImageDraw,ImageFont
TRACK='hk01_kam_tin_test';BUILD=ROOT/'driving_test';FULL=BUILD/'route_scenery';REPORTS=FULL/'reports';PACKAGE=ROOT/'release_route_scenery/content/tracks'/TRACK
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--install-root',type=Path);a=p.parse_args()
    validation=json.loads((REPORTS/'package_model_verification.json').read_text());surface=json.loads((REPORTS/'route_surface_verification.json').read_text());coverage=json.loads((FULL/'coverage.json').read_text());prepared=json.loads((FULL/'prepared_manifest.json').read_text())
    mipcheck=json.loads((REPORTS/'all_mip_verification.json').read_text())
    if not mipcheck['passed'] or mipcheck['prepared_manifest_sha256']!=digest(FULL/'prepared_manifest.json'):raise RuntimeError('Full mip verification missing, failed or stale')
    if not validation['passed'] or not surface['passed'] or coverage['uncovered_route_samples']:raise RuntimeError('Full-loop checks did not pass')
    if not validation.get('physical_meshes_unchanged') or not validation.get('spawn_timing_nodes_unchanged'):raise RuntimeError('Original physics/spawn invariant failed')
    for model in validation['models']:
        if digest(PACKAGE/model['filename'])!=model['kn5_sha256']:raise RuntimeError('Model validation is stale: '+model['filename'])
    if validation['total_texture_gpu_payload_bytes']>2*1024**3:raise RuntimeError('Texture memory budget exceeded')
    ini=configparser.ConfigParser();ini.read(PACKAGE/'models.ini');referenced={ini.get(section,'FILE') for section in ini.sections()}
    if referenced!={model['filename'] for model in validation['models']}:raise RuntimeError('Model list mismatch')
    baseline=ROOT/'release/content/tracks'/TRACK
    for part in ['data','sources']:shutil.copytree(baseline/part,PACKAGE/part,dirs_exist_ok=True)
    shutil.copy2(baseline/'map.png',PACKAGE/'map.png');(PACKAGE/'ui').mkdir(exist_ok=True)
    ui=json.loads((baseline/'ui/ui_track.json').read_text(encoding='utf-8'));ui['version']='0.3-full-loop';ui['description']='3.445 km Kam Tin solo driving test. Eight real Lands Department scenery tiles cover the full loop; the wider Hong Kong map remains unfinished. Temporary 7 m road, original collision/pit/spawns and eight numbered test markers. Practice, one car, clear daytime. No AI. Actual game loading and FPS await user test. Map from Lands Department; source data © Government of the Hong Kong SAR, https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.'
    (PACKAGE/'ui/ui_track.json').write_text(json.dumps(ui,indent=2,ensure_ascii=False),encoding='utf-8')
    im=Image.open(REPORTS/'csdi_sample_overview.png').convert('RGB').resize((1024,640));draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,1024,86),fill=(15,38,35));draw.text((22,8),'KAM TIN / FULL LOOP TEST 0.3',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',31),fill='white');draw.text((24,49),'3.445 KM  |  8 REAL SCENERY TILES  |  SOLO PRACTICE',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20),fill=(195,235,209))
    draw.rectangle((0,590,1024,640),fill=(245,245,245))
    with Image.open(ROOT/'source/csdi_individualised/landsd_logo_fb.jpg') as logo:
        logo=logo.convert('RGB');logo.thumbnail((43,43));im.paste(logo,(9,594))
    draw.text((65,595),'Map from Lands Department | © Government of the Hong Kong SAR',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17),fill=(20,45,35));draw.text((65,617),'3d.map.gov.hk | Roads © OpenStreetMap contributors',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15),fill=(20,45,35))
    im.save(PACKAGE/'ui/preview.png');im.save(PACKAGE/'ui/preview.jpg',quality=90);shutil.copy2(PACKAGE/'map.png',PACKAGE/'ui/outline.png')
    shutil.copy2(ROOT/'ATTRIBUTION.md',PACKAGE/'ATTRIBUTION.md');shutil.copy2(FULL/'TEST_ROUTE_GUIDE.png',PACKAGE/'TEST_ROUTE_GUIDE.png');shutil.copy2(FULL/'checkpoints.json',PACKAGE/'sources/checkpoints.json')
    terms=ROOT/'source/csdi_individualised/TERMS_SNAPSHOT_2026-11-13.txt'
    if not terms.is_file():terms=ROOT/'docs/LandsD_terms_snapshot.txt'
    shutil.copy2(terms,PACKAGE/'sources/LandsD_terms_snapshot.txt')
    source={'dataset':prepared['dataset'],'version':'0.3-full-loop','sheets':prepared['sheets'],'origin_epsg2326':prepared['origin_epsg2326'],'metres_per_unit':1,'detail_radius_m':prepared['detail_radius_m'],'source_manifest':json.loads((FULL/'source_manifest.json').read_text()),'missing_source_textures':prepared['missing_source_textures'],'adaptations':['local metre coordinates','route-corridor cropping','spatial batching and distance-based detail reduction','mipmapped DDS BC1 textures, maximum 2048 pixels','visual terrain blend; original driving collision retained'],'source_website':'https://3d.map.gov.hk/','data_ownership':'Government of the Hong Kong Special Administrative Region'}
    for name in ['csdi_sample.json','route_scenery.json']:(PACKAGE/'sources'/name).write_text(json.dumps(source,indent=2),encoding='utf-8')
    testing='''KAM TIN — FULL LOOP TEST 0.3

READY FOR YOUR OWN TEST
Track: Hong Kong — Kam Tin Driving Test
Mode: Practice. One player car, zero opponents. Clear daytime. Start from pits.
Use a standard Kunos road car first. Leave your usual graphics settings intact;
this build does not install CSP, weather mods, traffic or car dependencies.

1. Confirm the track loads, the car stands on pavement, and steering/throttle work.
2. Drive forward out of the left-side pit apron and merge onto the paved loop.
3. Complete a slow lap, keeping left and following the continuous road.
4. Pass the blue synthetic TEST POINT markers 1 through 8, then return to 1.
5. Check both lanes carefully for holes, bumps, invisible surfaces and barrier snags.
6. Try Return to pits. Confirm the car respawns upright on the apron.
7. Record FPS around the lap, especially dense scenery and corners. Report car,
   resolution, graphics/CSP settings, minimum FPS and the nearest checkpoint.

See TEST_ROUTE_GUIDE.png for checkpoint positions. If loading fails, send the
error message and the newest Documents/Assetto Corsa/logs/log.txt (review personal
paths before sharing). Nothing automatically uploads your logs.

WHAT THIS BUILD INCLUDES
The complete 3.445 km test loop, pit apron, start/timing nodes, road/shoulder/grass
collision, safety barriers, route markings, eight test markers, native minimap,
and adapted real Lands Department scenery from eight tiles covering the loop.
All source imagery/models and generated game files are local, not on GitHub.

LIMITS
This is the test loop, not all Hong Kong or every road in the 6 x 6 km blockout.
Neighbouring roads are scenery. Width/profile and barriers remain temporary.
Photogrammetry can look rough up close; some source textures need fallbacks.
Visual source scenery has no vehicle collision; the original test road and
barriers provide the driving collision. Night lighting, rain tuning, AI cars,
traffic and online racing are outside this solo daytime test.

The build passed static binary/image checks, lane-width surface ray tests,
baseline physics/spawn comparisons, protected-corridor checks, archive CRC and
installed-file hash checks. Actual engine loading, driving and FPS remain for
your test. No automatic game launch or graphics-setting changes were made.

Map from Lands Department. Source data © Government of the Hong Kong SAR.
https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.
See ATTRIBUTION.md and sources/LandsD_terms_snapshot.txt.
'''
    (PACKAGE/'TEST_README.txt').write_text(testing,encoding='utf-8');(PACKAGE/'TESTING.txt').write_text(testing,encoding='utf-8');(ROOT/'TESTING.md').write_text(testing,encoding='utf-8')
    files={str(p.relative_to(PACKAGE)).replace('\\','/'):p for p in PACKAGE.rglob('*') if p.is_file() and p.name!='manifest.json'}
    manifest={rel:{'bytes':p.stat().st_size,'sha256':digest(p)} for rel,p in sorted(files.items())};(PACKAGE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=ROOT.parent/'HK_KamTin_Full_Loop_Test_v0.3.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
        for rel,p in sorted(files.items()):z.write(p,'content/tracks/'+TRACK+'/'+rel)
        z.write(PACKAGE/'manifest.json','content/tracks/'+TRACK+'/manifest.json')
    with zipfile.ZipFile(archive) as z:
        if bad:=z.testzip():raise RuntimeError('ZIP CRC check failed: '+bad)
    report={'passed':True,'track_id':TRACK,'version':'0.3-full-loop','model_files':len(referenced),'scenery_tiles':prepared['sheets'],'route_coverage_percent':coverage['route_coverage_percent'],'route_length_m':3444.937762144697,'file_count':len(manifest)+1,'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive),'game_loading_driving_fps':'not performed; user will test','installed_to':None,'installed_file_hashes_verified':False}
    if a.install_root:
        ac=a.install_root.resolve();dest=ac/'content/tracks'/TRACK
        if not (ac/'acs.exe').is_file():raise RuntimeError('Not the verified Assetto Corsa installation')
        if dest.exists():
            if not (dest/'manifest.json').is_file():raise RuntimeError('Existing track is not owned by this package')
            old=json.loads((dest/'manifest.json').read_text());actual={str(p.relative_to(dest)).replace('\\','/') for p in dest.rglob('*') if p.is_file()}
            if actual!=set(old)|{'manifest.json'}:raise RuntimeError('Installed folder has changed; preserve user additions')
            if set(old)-set(manifest):raise RuntimeError('Update would leave obsolete files')
            for rel,info in old.items():
                if digest(dest/rel)!=info['sha256']:raise RuntimeError('Installed file edited; preserve user work: '+rel)
        shutil.copytree(PACKAGE,dest,dirs_exist_ok=True)
        for rel,info in manifest.items():
            if digest(dest/rel)!=info['sha256']:raise RuntimeError('Installed read-back failed: '+rel)
        if json.loads((dest/'manifest.json').read_text())!=manifest:raise RuntimeError('Installed manifest mismatch')
        report['installed_to']=str(dest);report['installed_file_hashes_verified']=True
    (REPORTS/'package_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
