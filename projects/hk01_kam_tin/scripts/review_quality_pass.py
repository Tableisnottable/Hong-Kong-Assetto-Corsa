"""Make a contact sheet; record a geometry review only after explicit inspection."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
from PIL import Image,ImageDraw,ImageFont
P=ROOT/'driving_test/quality_pass/reports'
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record-inspection',action='store_true');parser.add_argument('--notes');args=parser.parse_args()
    report=P/'quality_build.json';views=[];sheet=Image.new('RGB',(1600,1140),(22,29,27));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
    d.text((16,8),'v0.4 geometry review — Blender previews; Assetto Corsa appearance unverified',font=font,fill='white')
    for i in range(8):
        path=P/f'checkpoint_{i+1:02d}.png'
        if path.stat().st_mtime<report.stat().st_mtime:raise RuntimeError('Render predates build report: '+path.name)
        with Image.open(path) as im:im.load();thumb=im.convert('RGB').resize((400,250))
        x=(i%4)*400;y=45+(i//4)*282;sheet.paste(thumb,(x,y));d.text((x+8,y+253),f'Test point {i+1}',font=font,fill='white')
        views.append({'file':path.name,'sha256':digest(path)})
    for i,x in [(2,0),(6,800)]:
        with Image.open(P/f'checkpoint_{i+1:02d}.png') as im:sheet.paste(im.convert('RGB').resize((800,500)),(x,610))
    sheet.save(P/'all_checkpoints_contact_sheet.jpg',quality=94)
    if args.record_inspection:
        if not args.notes:raise RuntimeError('Record specific observations after inspecting all views')
        review={'geometry_review_passed':True,'quality_build_sha256':digest(report),'views':views,'inspection_notes':args.notes,'approval_scope':'Provisional visual repair for user comparison test; not production quality approval','assetto_corsa_appearance_fps_verified':False,'limits':['Generic authored foliage, not surveyed species.','Projected source ground retains photographic artifacts.','Temporary road width/profile, junctions and synthetic barriers.','Some unclassified raised structures removed with GENERIC data.','Game lighting and performance require a fresh user test.']}
        (P/'visual_review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
    print(P/'all_checkpoints_contact_sheet.jpg')
if __name__=='__main__':main()
