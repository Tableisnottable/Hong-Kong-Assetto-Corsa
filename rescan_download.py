import os, time, requests
PROJECT_DIR = r'C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa'
ZIP_FOLDER = os.path.join(PROJECT_DIR, 'all_3324_zips')
API_KEY = 'ad5940a63bd344c48b0351ef1c7a905e'
os.makedirs(ZIP_FOLDER, exist_ok=True)

tiles = [f'{m}-{s}-{i}{sub}' for m in range(1, 17) for s in ['NW', 'NE', 'SW', 'SE'] for i in range(1, 26) for sub in ['A', 'B', 'C', 'D']]

print(f'🔍 開始全盤重新掃描 3,324 個 Tile 清單...')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

downloaded = 0
skipped = 0

for idx, tile in enumerate(tiles, 1):
    zip_name = f'{tile}.zip'
    save_path = os.path.join(ZIP_FOLDER, zip_name)
    
    # 每次掃描檢查：如果檔案已存在且 >5KB，直接跳過
    if os.path.exists(save_path) and os.path.getsize(save_path) > 5000:
        skipped += 1
        continue
        
    url = f'https://data11.map.gov.hk/api/3d-zip/FBX/{zip_name}?&key={API_KEY}'
    
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            sz_mb = round(len(resp.content)/(1024*1024), 2)
            print(f'[{idx}/3324] 🟢 下載成功: {zip_name} ({sz_mb} MB)')
            downloaded += 1
        else:
            # 無模型或海洋區域，清除小於5KB的空檔
            if os.path.exists(save_path):
                os.remove(save_path)
    except Exception:
        pass

print(f'🎉 掃描完成！已跳過 {skipped} 個已存在檔案，本次成功下載 {downloaded} 個新模型。')
