"""Keep the installed CSP base camera behavior, with clearance for these buses."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
AC=Path('A:/SteamLibrary/steamapps/common/assettocorsa')
text=(AC/'extension/lua/chaser-camera/base/camera.lua').read_text(encoding='utf-8-sig')
needle='  local pitchAngle = cameraParameters.pitch - 5'
assert text.count(needle)==1
text=text.replace(needle,needle+'''

  -- Local bus conversions are longer than standard chase-camera distances.
  -- Apply clearance only to these two IDs; retain base behavior for other cars.
  local busID = ac.getCarID(car.index)
  if busID == 'kmb_e6m_drivable' then
    distance = cameraIndex == 1 and 14 or 18
    height = cameraIndex == 1 and 2.8 or 3.8
  elseif busID == 'kmb_e200_drivable' then
    distance = cameraIndex == 1 and 12.5 or 16
    height = cameraIndex == 1 and 2.4 or 3.2
  end
''')
(ROOT/'work/bus_chase_camera.lua').write_text(text,encoding='utf-8')
print('Prepared CSP base camera with bus-specific distances')
