"""Finish UI, package the verified test track, optionally install a new ID.
Does not launch Assetto Corsa or change any other track.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
deps=ROOT.parents[1]/'work/python_deps'
if deps.exists():sys.path.insert(0,str(deps))
from PIL import Image,ImageDraw,ImageFont
BUILD=ROOT/'driving_test';TRACK='hk01_kam_tin_test';RELEASE=ROOT/'release';PACKAGE=RELEASE/'content/tracks'/TRACK

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install-root',type=Path);args=parser.parse_args()
    scene=json.loads((BUILD/'reports/scene_collision_verification.json').read_text(encoding='utf-8'))
    binary=json.loads((BUILD/'reports/kn5_external_verification.json').read_text(encoding='utf-8'))
    if not scene['passed'] or not binary['passed']:raise RuntimeError('Track checks did not pass')
    kn5=PACKAGE/(TRACK+'.kn5')
    # A report must refer to this exact final exported binary.
    if binary.get('file_bytes')!=kn5.stat().st_size or binary.get('kn5_sha256')!=digest(kn5):raise RuntimeError('Binary report is stale; rerun verification')
    im=Image.open(BUILD/'reports/test_track_start.png').convert('RGB')
    im=im.resize((1024,640));draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,1024,92),fill=(18,32,40))
    draw.text((28,14),'HONG KONG / KAM TIN',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',36),fill=(238,242,231))
    draw.text((30,57),'3.45 KM DRIVING TEST 0.1 — SOLO PRACTICE',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21),fill=(145,220,194))
    im.save(PACKAGE/'ui/preview.png');im.save(PACKAGE/'ui/preview.jpg',quality=92)
    shutil.copy2(PACKAGE/'map.png',PACKAGE/'ui/outline.png')
    shutil.copy2(ROOT/'ATTRIBUTION.md',PACKAGE/'ATTRIBUTION.md')
    (PACKAGE/'sources').mkdir(exist_ok=True)
    shutil.copy2(BUILD/'source/test_loop_source.json',PACKAGE/'sources/test_loop_source.json')
    shutil.copy2(BUILD/'reports/route_build.json',PACKAGE/'sources/route_build.json')
    # Correct standalone-track metadata and surface names are checked before install.
    required=['models.ini',TRACK+'.kn5','data/surfaces.ini','data/lighting.ini','data/map.ini','ui/ui_track.json','ui/preview.png','ui/outline.png','map.png','TEST_README.txt']
    for rel in required:
        if not (PACKAGE/rel).is_file():raise RuntimeError('Missing package file '+rel)
    ui=json.loads((PACKAGE/'ui/ui_track.json').read_text(encoding='utf-8'))
    if str(ui['pitboxes'])!='1':raise RuntimeError('First test has one verified pit box')
    manifest={str(p.relative_to(PACKAGE)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(PACKAGE.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (PACKAGE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    zip_path=ROOT.parents[0]/'HK_KamTin_Driving_Test_v0.1.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(PACKAGE.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(RELEASE)).replace('\\','/'))
    with zipfile.ZipFile(zip_path) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP verification failed: '+bad)
    result={'track_id':TRACK,'display_name':ui['name'],'kn5_sha256':digest(kn5),'archive':str(zip_path),'archive_sha256':digest(zip_path),'archive_bytes':zip_path.stat().st_size,'package_files':len(manifest)+1,'installed_to':None,'game_driving_test':'not performed; user will test','ai_opponents_supported':False,'scene_checks_passed':True,'binary_checks_passed':True}
    if args.install_root:
        ac=args.install_root.resolve()
        if not (ac/'acs.exe').is_file() or not (ac/'content/tracks').is_dir():raise RuntimeError('Not the verified Assetto Corsa installation')
        destination=ac/'content/tracks'/TRACK
        if destination.exists():
            # Only update this task's new track when its previous package is unchanged.
            oldmanifest=destination/'manifest.json'
            if not oldmanifest.is_file():raise RuntimeError('Existing destination not owned by this package; refusing overwrite')
            old=json.loads(oldmanifest.read_text(encoding='utf-8'))
            actual={str(p.relative_to(destination)).replace('\\','/') for p in destination.rglob('*') if p.is_file()}
            if actual!=set(old)|{'manifest.json'}:raise RuntimeError('Installed destination has extra/missing files; preserve user edits')
            for rel,info in old.items():
                if digest(destination/rel)!=info['sha256']:raise RuntimeError('Installed destination has changes; preserve user edits')
        shutil.copytree(PACKAGE,destination,dirs_exist_ok=True)
        for rel,info in manifest.items():
            if digest(destination/rel)!=info['sha256']:raise RuntimeError('Installed readback mismatch: '+rel)
        result['installed_to']=str(destination);result['installed_file_hashes_verified']=True
    (BUILD/'reports/package_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
