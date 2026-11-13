"""Prepare photographed surfaces and newly composed alpha-tested foliage sprays."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
SOURCE=ROOT/'source/finish_library';OUT=ROOT/'driving_test/finish_pass';TEXTURES=OUT/'textures'
def main():
    TEXTURES.mkdir(parents=True,exist_ok=True);(OUT/'reports').mkdir(exist_ok=True)
    rng=np.random.default_rng(2026111405)
    p=SOURCE/'island_tree_01';diff=Image.open(p/'island_tree_01_leaves_diff_1k.png').convert('RGBA');a=np.asarray(Image.open(p/'island_tree_01_leaves_alpha_1k.png'));a=np.uint8(a.astype(float)/(257 if a.max()>255 else 1));a[np.asarray(diff)[:,:,:3].min(axis=2)>180]=0;diff.putalpha(Image.fromarray(a).filter(ImageFilter.MinFilter(3)))
    leaves=[]
    for box in [(0,0,256,510),(256,0,512,510),(512,0,768,510),(768,0,1024,510),(0,512,290,1024),(300,512,630,1024),(650,512,1024,1024)]:
        im=diff.crop(box);bbox=im.getchannel('A').getbbox()
        if bbox:leaves.append(im.crop(bbox))
    atlas=Image.new('RGBA',(1024,1024),(42,60,27,0))
    for tile in range(4):
        spray=Image.new('RGBA',(512,512),(42,60,27,0));d=ImageDraw.Draw(spray)
        d.line([(260,489),(246,345),(267,220),(247,45)],fill=(75,83,40,255),width=5)
        for i in range(11):
            side=-1 if i%2 else 1;y=452-i*35;x=255+side*(72+int(rng.integers(-16,17)));d.line((255,y+16,x,y-30),fill=(75,83,40,255),width=3)
            im=leaves[int(rng.integers(0,len(leaves)))].copy();im.thumbnail((int(rng.integers(88,123)),int(rng.integers(128,180))),Image.Resampling.LANCZOS)
            im=im.rotate(side*float(rng.uniform(35,68)),resample=Image.Resampling.BICUBIC,expand=True)
            spray.alpha_composite(im,(int(x-im.width/2),int(y-im.height*.65)))
        atlas.alpha_composite(spray,((tile%2)*512,(tile//2)*512))
    # Fill transparent RGB with green to keep mip/filter edges from turning white.
    arr=np.array(atlas);rgb=arr[:,:,:3].astype(float);rgb*=np.array([.80,1.01,.86]);arr[:,:,:3]=np.uint8(np.clip(rgb,0,255));Image.fromarray(arr).save(TEXTURES/'hk_foliage_sprays.png')
    bark=Image.open(p/'island_tree_01_branches_diff_1k.png').convert('RGB');bark.save(TEXTURES/'hk_bark_photo.png')
    for asset,file,out in [('asphalt_02','asphalt_02_diff_2k.jpg','hk_asphalt_photo.png'),('aerial_grass_rock','aerial_grass_rock_diff_2k.jpg','hk_ground_photo.png')]:
        im=Image.open(SOURCE/asset/file).convert('RGB')
        if asset=='aerial_grass_rock':
            # Generic 75 m fallback ground composition, not a Hong Kong survey.
            a=np.asarray(im).astype(float)*np.array([.58,.82,.63]);im=Image.fromarray(np.uint8(np.clip(a,0,255)))
            mosaic=Image.new('RGB',(2050,2050))
            for y in range(5):
                for x in range(5):
                    tile=im.rotate(int(rng.integers(0,4))*90).resize((410,410),Image.Resampling.LANCZOS);mosaic.paste(tile,(x*410,y*410))
            im=mosaic.resize((2048,2048),Image.Resampling.LANCZOS)
        im.save(TEXTURES/out)
    n=rng.normal(0,4,(1024,1024));base=np.clip(177+n,145,194);rgba=np.empty((1024,1024,4),dtype=np.uint8);rgba[:,:,:3]=np.uint8(base[:,:,None]*np.array([1,1,.96]));rgba[:,:,3]=np.where(rng.random((1024,1024))<.065,0,255);Image.fromarray(rgba).save(TEXTURES/'hk_worn_paint.png')
    steel=np.clip(137+rng.normal(0,5,(512,512)),95,165);Image.fromarray(np.uint8(steel[:,:,None]*np.array([.97,.99,1.03]))).save(TEXTURES/'hk_galvanised_steel.png')
    for name,color in [('hk_post_dark.png',(76,81,82)),('hk_reflector_red.png',(145,18,16)),('hk_reflector_white.png',(190,192,182))]:Image.new('RGB',(32,32),color).save(TEXTURES/name)
    result={'reference':'Installed Route Twisk RWE / Repack Test, read-only quality benchmark','reference_assets_reused':False,'source_manifest':'source/finish_library/manifest.json','authored_foliage_spray_variants':4,'source_leaf_species_not_claimed_as_local_survey':True,'leaf_alpha_16bit_to_8bit_conversion':True,'textures':[p.name for p in TEXTURES.glob('*.png')]}
    (OUT/'reports/preparation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
