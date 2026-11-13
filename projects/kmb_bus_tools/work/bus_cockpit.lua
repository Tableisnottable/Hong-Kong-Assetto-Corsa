-- Runtime cockpit telemetry. Binding names and gauge curves come from the
-- user's local OMSI models. Steering remains on the native AC steering node.
local root = ac.findNodes('carRoot:' .. car.index)
local speed = root:findNodes('KMB_SPEED_MOTION')
local rpm = root:findNodes('KMB_RPM_MOTION')
local temperature = root:findNodes('KMB_TEMP_MOTION')
local pedalBrake = root:findNodes('KMB_BRAKE_MOTION')
local pedalGas = root:findNodes('KMB_GAS_MOTION')
local parkingBrake = root:findNodes('KMB_HANDBRAKE_MOTION')
local wiperL = root:findNodes('KMB_WIPER_L')
local wiperR = root:findNodes('KMB_WIPER_R')
local tagL = root:findNodes('E6M_TAG_LR')
local tagR = root:findNodes('E6M_TAG_RR')
local tagAngle = 0
local wipersEnabled = false
local wiperPhase = 0
local function clamp(v, lo, hi) return math.max(lo, math.min(v, hi)) end
local function interpolate(points, value)
  if value <= points[1][1] then return points[1][2] end
  for i = 2, #points do
    if value <= points[i][1] then
      local a, b = points[i - 1], points[i]
      return a[2] + (b[2] - a[2]) * (value - a[1]) / (b[1] - a[1])
    end
  end
  return points[#points][2]
end
local function meshes(names)
  local list = {}
  for _, name in ipairs(names) do
    list[#list + 1] = root:findMeshes(name):ensureUniqueMaterials()
  end
  return list
end
local indicators, gears = {}, {}
for key, names in pairs(bindings.indicators) do indicators[key] = meshes(names) end
for key, names in pairs(bindings.gearMeshes) do gears[key] = meshes(names) end
local backlit = meshes(bindings.backlit)
local function glow(list, enabled, color)
  if not list then return end
  local value = enabled and color or rgb(0, 0, 0)
  for _, mesh in ipairs(list) do mesh:setMaterialProperty('ksEmissive', value) end
end
local clicks = {}
for key, name in pairs(bindings.buttons) do
  clicks[key] = display.interactiveMesh{ mesh = name }.clicked()
end
local pageClick = display.interactiveMesh{ mesh = 'KMB_DRIVER_LCD' }.clicked()
local page = 1
local function text(value, x, y, w, h)
  display.text{ text = tostring(value), pos = vec2(x, y), letter = vec2(w, h),
    font = 'aria', color = rgbm(0.62, 0.82, 0.68, 1) }
end
function script.update(dt)
  local velocity = math.abs(car.speedKmh)
  speed:setRotation(vec3(0, 0, 1), math.rad(interpolate(bindings.speedCurve, velocity)))
  rpm:setRotation(vec3(0, 0, 1), math.rad(interpolate(bindings.rpmCurve, car.rpm)))
  temperature:setRotation(vec3(0, 0, 1), math.rad(interpolate(bindings.tempCurve, car.waterTemperature)))
  if bindings.hasPedals then
    pedalBrake:setRotation(vec3(1, 0, 0), math.rad(25 * car.brake))
    pedalGas:setRotation(vec3(1, 0, 0), math.rad(25 * car.gas))
    parkingBrake:setRotation(vec3(1, 0, 0), math.rad(-70 * car.handbrake))
  end
  local wiperRunning = wipersEnabled or car.wiperSelectedMode > 0
  if wiperRunning or wiperPhase > 0 then
    wiperPhase = wiperPhase + dt * 0.65
    if wiperPhase >= 1 then wiperPhase = wiperRunning and wiperPhase % 1 or 0 end
  end
  local sweep = (1 - math.cos(wiperPhase * math.pi * 2)) / 2
  wiperL:setRotation(vec3(0, 0, 1), math.rad(-75 * sweep))
  wiperR:setRotation(vec3(0, 0, 1), math.rad(75 * sweep))
  if bindings.car == 'E6M' then
    tagAngle = (tagAngle + car.speedKmh / 3.6 / 0.49925 * dt) % (2 * math.pi)
    tagL:setRotation(vec3(1, 0, 0), tagAngle)
    tagR:setRotation(vec3(1, 0, 0), tagAngle)
  end
  glow(indicators.handbrake, car.handbrake > 0.1, rgb(3, 0.06, 0.02))
  glow(indicators.battery, car.rpm < 300, rgb(3, 0.06, 0.02))
  glow(indicators.warning, car.waterTemperature > 105, rgb(3, 0.06, 0.02))
  glow(indicators.highbeam, car.highBeams, rgb(0.03, 0.1, 3))
  glow(indicators.lights, car.headlightsActive, rgb(0.05, 2, 0.05))
  glow(indicators.left, car.turningLeftLights and car.turningLightsActivePhase, rgb(0.05, 3, 0.04))
  glow(indicators.right, car.turningRightLights and car.turningLightsActivePhase, rgb(0.05, 3, 0.04))
  glow(indicators.turn, car.turningLightsActivePhase and (car.turningLeftLights or car.turningRightLights), rgb(0.05, 3, 0.04))
  glow(indicators.abs, car.absInAction, rgb(3, 1.5, 0.02))
  glow(backlit, car.headlightsActive, rgb(0.7, 0.65, 0.45))
  local gear = car.gear < 0 and 'R' or car.gear == 0 and 'N' or 'D'
  for key, list in pairs(gears) do glow(list, key == gear, rgb(0.12, 1.2, 0.1)) end
  if clicks.headlights() then ac.setHeadlights(not car.headlightsActive) end
  if clicks.hazards() then ac.setTurningLights(car.hazardLights and ac.TurningLights.None or ac.TurningLights.Hazards) end
  if clicks.left() then ac.setTurningLights(car.turningLeftOnly and ac.TurningLights.None or ac.TurningLights.Left) end
  if clicks.right() then ac.setTurningLights(car.turningRightOnly and ac.TurningLights.None or ac.TurningLights.Right) end
  if clicks.neutral() and velocity < 1 then ac.switchToNeutralGear() end
  if clicks.highbeam and clicks.highbeam() then ac.setHighBeams(not car.highBeams) end
  if clicks.wipers and clicks.wipers() then
    wipersEnabled = not wipersEnabled
    if car.wiperModes > 1 then ac.setWiperMode(wipersEnabled and 1 or 0) end
  end
  if pageClick() then page = page == 1 and 2 or 1 end
  display.rect{ pos = vec2(0, 0), size = vec2(512, 256), color = rgbm(0.025, 0.055, 0.04, 1) }
  text('KMB', 16, 8, 16, 25)
  text(gear .. (car.gear > 0 and tostring(car.gear) or ''), 396, 8, 28, 40)
  if page == 1 then
    text(string.format('%03d', math.floor(velocity + 0.5)), 14, 40, 45, 68)
    text('km/h', 156, 76, 16, 26)
    text(string.format('%4d RPM', math.floor(car.rpm + 0.5)), 14, 124, 21, 32)
    text(string.format('%3d L', math.floor(car.fuel)), 304, 124, 21, 32)
    text(string.format('WATER %3d C', math.floor(car.waterTemperature)), 14, 174, 18, 28)
    text(car.handbrake > 0.1 and 'PARK' or '', 388, 180, 19, 30)
    text(string.format('TRIP %.1f km', car.distanceDrivenSessionKm), 14, 218, 16, 24)
  else
    text(string.format('FUEL      %.1f L', car.fuel), 18, 68, 24, 38)
    text(string.format('COOLANT   %.0f C', car.waterTemperature), 18, 120, 24, 38)
    text(string.format('BATTERY   %.1f V', car.batteryVoltage), 18, 172, 24, 38)
    text(car.headlightsActive and 'LIGHTS ON' or 'LIGHTS OFF', 18, 220, 16, 24)
  end
end
