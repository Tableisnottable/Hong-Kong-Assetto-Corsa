-- HK Driving Test Exam System
-- Route guidance + scoring for Hong Kong driving test simulation
-- Uses CSP Lua app API: manifest.ini + script.windowMain / script.update

local sim = ac.getSim()

-- ---------------------------------------------------------------------------
-- State
-- ---------------------------------------------------------------------------
local state = {
  active = false,
  finished = false,
  centre = nil,
  routeId = nil,
  route = nil,
  step = 1,
  score = 100,
  deductions = {},
  distance = 0,
  lastPos = nil,
  lastSpeed = 0,
  collisionCooldown = 0,
  stoppedTime = 0,
  stopCounted = false,
  startTime = 0,
  duration = 0,
}

local settings = ac.storage({
  speedLimit = 50,
  autoAdvance = true,
  stepDistance = 300,
})

-- ---------------------------------------------------------------------------
-- Routes
-- ---------------------------------------------------------------------------
local routes = dofile('apps/lua/hk_exam/routes.lua') or {}

local routeIds = {}
for id in pairs(routes) do routeIds[#routeIds + 1] = id end
table.sort(routeIds)

local selectedRoute = 1

local function currentRouteId()
  return routeIds[selectedRoute]
end

-- ---------------------------------------------------------------------------
-- Scoring
-- ---------------------------------------------------------------------------
local function deduct(points, reason, cooldown)
  if not state.active then return end
  local now = os.preciseClock()
  if cooldown then
    for i = #state.deductions, 1, -1 do
      local d = state.deductions[i]
      if d.reason == reason and now - d.time < cooldown then return end
    end
  end
  state.score = math.max(0, state.score - points)
  state.deductions[#state.deductions + 1] = {
    step = state.step,
    points = points,
    reason = reason,
    time = now,
  }
  ac.log(('[HK Exam] -%d pts: %s (score %d)'):format(points, reason, state.score))
end

local function finishExam()
  if not state.active then return end
  state.active = false
  state.finished = true
  state.duration = os.preciseClock() - state.startTime
  local result = state.score >= 70 and 'PASS' or 'FAIL'
  ac.log(('[HK Exam] finished: %s (%d)'):format(result, state.score))
  ac.setSystemMessage('HK Exam', ('考試完畢: %s (%d 分)'):format(result, state.score))
end

local function advanceStep(manual)
  if not state.active then return end
  local total = state.route and #state.route.steps or 0
  if state.step >= total then
    finishExam()
    return
  end
  state.step = state.step + 1
  if not manual then
    ac.log(('[HK Exam] auto-advance to step %d'):format(state.step))
  end
end

local function startExam()
  local id = currentRouteId()
  state.route = routes[id]
  if not state.route then
    ac.setSystemMessage('HK Exam', 'Route not found: ' .. tostring(id))
    return
  end
  state.active = true
  state.finished = false
  state.centre = state.route.centre
  state.routeId = id
  state.step = 1
  state.score = 100
  state.deductions = {}
  state.distance = 0
  state.lastPos = nil
  state.lastSpeed = 0
  state.collisionCooldown = 0
  state.stoppedTime = 0
  state.stopCounted = false
  state.startTime = os.preciseClock()
  state.duration = 0
  ac.setSystemMessage('HK Exam', ('考試開始: %s (%d 步)'):format(state.route.name, #state.route.steps))
end

-- ---------------------------------------------------------------------------
-- Update
-- ---------------------------------------------------------------------------
function script.update(dt)
  if not state.active then return end
  local car = ac.getCar(0)
  if not car then return end

  local pos = car.position
  local speed = car.speedKmh

  -- distance travelled (ignore teleports)
  if state.lastPos then
    local d = pos:distance(state.lastPos)
    if d < 20 then state.distance = state.distance + d end
  end
  state.lastPos = pos:clone()

  -- speed limit
  local limit = settings.speedLimit
  if speed > limit + 5 then
    if speed > limit + 20 then
      deduct(15, ('嚴重超速 %.0f km/h'):format(speed), 5)
    elseif speed > limit + 10 then
      deduct(10, ('超速 %.0f km/h'):format(speed), 5)
    else
      deduct(5, ('超速 %.0f km/h'):format(speed), 5)
    end
  end

  -- collision (speed sudden drop while slow)
  if state.lastSpeed - speed > 25 and speed < 30 and state.collisionCooldown <= 0 then
    deduct(15, '碰撞事故', 10)
    state.collisionCooldown = 10
  end
  state.lastSpeed = speed
  state.collisionCooldown = math.max(0, state.collisionCooldown - dt)

  -- unnecessary stop
  if speed < 1 then
    state.stoppedTime = state.stoppedTime + dt
    if state.stoppedTime > 3 and not state.stopCounted then
      deduct(5, '無故停車超過3秒', 30)
      state.stopCounted = true
    end
  else
    state.stoppedTime = 0
    state.stopCounted = false
  end

  -- auto step advance by distance
  if settings.autoAdvance and state.route then
    local expected = state.step * settings.stepDistance
    if state.distance > expected and state.step < #state.route.steps then
      advanceStep(false)
    end
  end
end

-- ---------------------------------------------------------------------------
-- UI
-- ---------------------------------------------------------------------------
local function drawIdle()
  ui.header('香港駕駛考試系統')
  ui.text('選擇路線:')
  ui.combo('##route', routes[currentRouteId()].name, ui.ComboFlags.None, function()
    for _, id in ipairs(routeIds) do
      ui.selectable(routes[id].name, id == currentRouteId(), 0, vec2(0, 0))
      if ui.itemClicked() then
        selectedRoute = table.indexOf(routeIds, id)
      end
    end
  end)
  ui.separator()
  if ui.button('開始考試 (F5)', vec2(-0.1, 0)) then
    startExam()
  end
  ui.textWrapped('規則: 起始100分, 70分合格。超速-5至-15, 碰撞-15, 無故停車-5。')
end

local function drawSummary()
  local pass = state.score >= 70
  ui.header(pass and '考試合格 PASS' or '考試不合格 FAIL')
  ui.textColored(('總分: %d / 100'):format(state.score), pass and rgbm.colors.lime or rgbm.colors.red)
  local m = math.floor(state.duration / 60)
  local s = math.floor(state.duration % 60)
  ui.text(('時間: %d:%02d  距離: %.0f m'):format(m, s, state.distance))
  ui.separator()
  ui.text('扣分明細:')
  if #state.deductions == 0 then
    ui.textColored('無扣分', rgbm.colors.lime)
  else
    for i, d in ipairs(state.deductions) do
      ui.textColored(('%d. -%d分 %s'):format(i, d.points, d.reason), rgbm.colors.red)
    end
  end
  ui.separator()
  if ui.button('重新考試 (F5)', vec2(-0.1, 0)) then
    startExam()
  end
end

local function drawActive()
  local route = state.route
  local total = route and #route.steps or 0

  ui.header(route and route.name or '考試')
  local scoreColor = state.score >= 85 and rgbm.colors.lime
    or state.score >= 70 and rgbm.colors.yellow
    or rgbm.colors.red
  ui.textColored(('分數: %d / 100'):format(state.score), scoreColor)

  if total > 0 then
    ui.progressBar((state.step - 1) / total, vec2(-0.1, 0),
      ('步驟 %d / %d'):format(state.step, total))
  end

  local step = route and route.steps[state.step]
  if step then
    ui.separator()
    ui.text('下一步指示:')
    ui.textWrapped(step.instruction)
    local turnText = ({
      L = '◄ 左轉',
      R = '右轉 ►',
      FINISH = '★ 完成',
      STRAIGHT = '↑ 直行',
      ROUNDABOUT = '◎ 迴旋處',
      UTURN = '⟲ 掉頭',
      SLOPE_START = '⛰ 斜路起步',
      SLOPE_UP = '⛰ 上斜',
      REVERSE_L_PARK = '🅿 倒後泊車',
      S_PARK = '🅿 停車',
      MERGE = '⇉ 匯入',
      LANE_CHANGE = '⇄ 變線',
      TUNNEL = ' tunnel',
    })[step.turn] or step.turn
    ui.textColored(turnText, rgbm.colors.cyan)
  else
    ui.textColored('路線完成!', rgbm.colors.lime)
  end

  local car = ac.getCar(0)
  if car then
    local limit = settings.speedLimit
    local sp = car.speedKmh
    local spColor = sp > limit + 5 and rgbm.colors.red
      or sp > limit and rgbm.colors.yellow
      or rgbm.colors.lime
    ui.textColored(('時速: %.0f km/h (限速 %d)'):format(sp, limit), spColor)
  end

  ui.text(('行駛: %.0f m'):format(state.distance))

  ui.separator()
  ui.text('扣分記錄:')
  if #state.deductions == 0 then
    ui.textColored('暫無扣分', rgbm.colors.lime)
  else
    for i = math.max(1, #state.deductions - 5), #state.deductions do
      local d = state.deductions[i]
      ui.textColored(('- %d分: %s'):format(d.points, d.reason), rgbm.colors.red)
    end
  end

  ui.separator()
  if ui.button('結束考試 (F6)', vec2(-0.1, 0)) then
    finishExam()
  end
  ui.sameLine()
  if ui.button('下一步 (F7)', vec2(-0.1, 0)) then
    advanceStep(true)
  end
end

function script.windowMain(dt)
  if state.finished then
    drawSummary()
  elseif state.active then
    drawActive()
  else
    drawIdle()
  end
end

function script.windowSettings(dt)
  settings.speedLimit = ui.slider('##limit', settings.speedLimit, 30, 80, '限速: %d km/h')
  settings.autoAdvance = ui.checkbox('自動推進步驟 (按距離)', settings.autoAdvance)
  settings.stepDistance = ui.slider('##stepdist', settings.stepDistance, 100, 1000, '每步距離: %d m')
end

-- ---------------------------------------------------------------------------
-- Hotkeys (via ControlButton so they can be rebound in AC controls)
-- ---------------------------------------------------------------------------
local startButton = ac.ControlButton('__APP_HK_EXAM_START')
local endButton = ac.ControlButton('__APP_HK_EXAM_END')
local nextButton = ac.ControlButton('__APP_HK_EXAM_NEXT')

function script.updateHotkeys()
  if startButton:pressed() and not state.active then
    startExam()
  end
  if endButton:pressed() and state.active then
    finishExam()
  end
  if nextButton:pressed() and state.active then
    advanceStep(true)
  end
end
