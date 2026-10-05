import asyncio, os, aiohttp
PROJECT_DIR = r'C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa'
ZIP_FOLDER = os.path.join(PROJECT_DIR, 'all_3324_zips')
API_KEY = 'ad5940a63bd344c48b0351ef1c7a905e'
CONCURRENCY_LIMIT = 16
os.makedirs(ZIP_FOLDER, exist_ok=True)
for f in os.listdir(ZIP_FOLDER):
    if f.endswith('.invalid'):
        try: os.remove(os.path.join(ZIP_FOLDER, f))
        except: pass
tiles = [f'{m}-{s}-{i}{sub}' for m in range(1, 17) for s in ['NW', 'NE', 'SW', 'SE'] for i in range(1, 26) for sub in ['A', 'B', 'C', 'D']]
pending_tiles = [t for t in tiles if not (os.path.exists(os.path.join(ZIP_FOLDER, f'{t}.zip')) and os.path.getsize(os.path.join(ZIP_FOLDER, f'{t}.zip')) > 5000)]
total_pending = len(pending_tiles)
print(f'🚀 正向升序 (ASC) 啟動！掃描 {total_pending} 個未完成 Tile...')
completed = 0
async def download_tile(session, semaphore, tile_name):
    global completed
    zip_name = f'{tile_name}.zip'
    save_path = os.path.join(ZIP_FOLDER, zip_name)
    url = f'https://data11.map.gov.hk/api/3d-zip/FBX/{zip_name}?&key={API_KEY}'
    async with semaphore:
        try:
            async with session.get(url, timeout=12) as resp:
                completed += 1
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) > 5000:
                        with open(save_path, 'wb') as f: f.write(content)
                        print(f'[{completed}/{total_pending}] 🟢 下載成功: {zip_name} ({round(len(content)/(1024*1024), 2)} MB)')
        except Exception:
            pass
async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        await asyncio.gather(*[download_tile(session, semaphore, t) for t in pending_tiles])
if __name__ == '__main__':
    asyncio.run(main())
    print('🎉 升序下載完成！')
