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

-- TD special traffic news (refresh with tools/fetch_td_news.py)
local tdNews = dofile('apps/lua/hk_exam/td_news.lua') or {}

local CATEGORY_LABEL = {
  accident = '交通意外',
  roadworks = '道路工程',
  congestion = '交通擠塞',
  closure = '道路封閉',
  reopened = '已解封',
  weather = '天氣影響',
  event = '特別活動',
  other = '其他消息',
}

local showNews = false
local showBusRoutes = false

-- Real bus routes serving each centre district (660 codes, 13 centres)
local busRoutes = dofile('apps/lua/hk_exam/bus_routes.lua') or {}

-- Map route id -> track id so the panel follows the selected route.
local CENTRE_TO_TRACK = {
  tin_kwong_1 = 'hong_kong_1to1',
  tin_kwong_2 = 'hong_kong_1to1',
  tin_kwong_3 = 'hong_kong_1to1',
  sheung_on_1 = 'hong_kong_1to1_sheung_on',
  texaco_1 = 'hong_kong_1to1_texaco',
  texaco_2 = 'hong_kong_1to1_texaco',
  texaco_3 = 'hong_kong_1to1_texaco',
  happy_valley_1 = 'hong_kong_1to1_happy_valley',
  happy_valley_2 = 'hong_kong_1to1_happy_valley',
  so_kun_po_1 = 'hong_kong_1to1_so_kun_po',
  so_kun_po_2 = 'hong_kong_1to1_so_kun_po',
  so_kun_po_3 = 'hong_kong_1to1_so_kun_po',
  so_kun_po_4 = 'hong_kong_1to1_so_kun_po',
  shek_am_1 = 'hong_kong_1to1_shek_am',
  shek_am_2 = 'hong_kong_1to1_shek_am',
  yau_tong_1 = 'hong_kong_1to1_yau_tong',
  yau_tong_2 = 'hong_kong_1to1_yau_tong',
  chung_ngai_1 = 'hong_kong_1to1_chung_ngai',
  chung_ngai_2 = 'hong_kong_1to1_chung_ngai',
  pui_ching_1 = 'hong_kong_1to1_pui_ching',
  pui_ching_2 = 'hong_kong_1to1_pui_ching',
  pui_ching_3 = 'hong_kong_1to1_pui_ching',
  pui_ching_4 = 'hong_kong_1to1_pui_ching',
  wing_hau_1 = 'hong_kong_1to1_wing_hau',
  wing_hau_2 = 'hong_kong_1to1_wing_hau',
  ap_lei_chau_1 = 'hong_kong_1to1_ap_lei_chau',
  ap_lei_chau_2 = 'hong_kong_1to1_ap_lei_chau',
  yuen_long_1 = 'hong_kong_1to1_yuen_long',
  yuen_long_2 = 'hong_kong_1to1_yuen_long',
  sha_tin_1 = 'hong_kong_1to1_sha_tin',
  sha_tin_2 = 'hong_kong_1to1_sha_tin',
}

local function currentTrackId()
  return CENTRE_TO_TRACK[currentRouteId()] or 'hong_kong_1to1'
end

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
  ui.separator()
  if ui.button(('即時交通消息 (%d)'):format(#tdNews), vec2(-0.1, 0)) then
    showNews = not showNews
  end  if showNews then
    if #tdNews == 0 then
      ui.textColored('暫無消息 (執行 tools/fetch_td_news.py 更新)', rgbm.colors.gray)
    else
      for i, item in ipairs(tdNews) do
        if i > 8 then break end
        local label = CATEGORY_LABEL[item.category] or item.category
        local color = item.reopened and rgbm.colors.gray or rgbm.colors.orange
        ui.textColored(('[%s] %s'):format(label, item.title_zh), color)
      end
      if #tdNews > 8 then
        ui.textColored(('... 另有 %d 則'):format(#tdNews - 8), rgbm.colors.gray)
      end
    end
  end

  local trackId = currentTrackId()
  local routesHere = busRoutes[trackId] or {}
  ui.separator()
  if ui.button(('本區巴士路線 (%d)'):format(#routesHere), vec2(-0.1, 0)) then
    showBusRoutes = not showBusRoutes
  end
  if showBusRoutes then
    if #routesHere == 0 then
      ui.textColored('暫無路線資料', rgbm.colors.gray)
    else
      local line = ''
      for i, code in ipairs(routesHere) do
        if i > 24 then
          line = line .. ' ...'
          break
        end
        line = (i == 1) and code or (line .. ', ' .. code)
      end
      ui.pushTextWrapPosition(320)
      ui.textWrapped(line)
      ui.popTextWrapPosition()
    end
  end
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

startButton:onPressed(function()
  if not state.active then startExam() end
end)
endButton:onPressed(function()
  if state.active then finishExam() end
end)
nextButton:onPressed(function()
  if state.active then advanceStep(true) end
end)
