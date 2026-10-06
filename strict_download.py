import os, time, requests
PROJECT_DIR = r'C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa'
ZIP_FOLDER = os.path.join(PROJECT_DIR, 'all_3324_zips')
API_KEY = 'ad5940a63bd344c48b0351ef1c7a905e'
os.makedirs(ZIP_FOLDER, exist_ok=True)

tiles = [f'{m}-{s}-{i}{sub}' for m in range(1, 17) for s in ['NW', 'NE', 'SW', 'SE'] for i in range(1, 26) for sub in ['A', 'B', 'C', 'D']]
pending_tiles = [t for t in tiles if not (os.path.exists(os.path.join(ZIP_FOLDER, f'{t}.zip')) and os.path.getsize(os.path.join(ZIP_FOLDER, f'{t}.zip')) > 5000)]

total_pending = len(pending_tiles)
print(f'🛡️ 啟動嚴格逐一 (ASC) 重試下載！總共待檢查 Tile: {total_pending}')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

completed = 0
for tile in pending_tiles:
    completed += 1
    zip_name = f'{tile}.zip'
    save_path = os.path.join(ZIP_FOLDER, zip_name)
    url = f'https://data11.map.gov.hk/api/3d-zip/FBX/{zip_name}?&key={API_KEY}'
    
    success = False
    for attempt in range(1, 3):
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(save_path, 'wb') as f:
                    f.write(resp.content)
                sz_mb = round(len(resp.content)/(1024*1024), 2)
                print(f'[{completed}/{total_pending}] 🟢 [成功下載] {zip_name} ({sz_mb} MB)')
                success = True
                break
            elif resp.status_code == 404 or len(resp.content) <= 5000:
                # 確定係海洋/無模型區域
                break
        except Exception as e:
            time.sleep(1)
            
    if not success and completed % 50 == 0:
        print(f'[{completed}/{total_pending}] 🔍 正進行地毯式推進中...')

print('🎉 嚴格地毯式掃描下載完成！')
