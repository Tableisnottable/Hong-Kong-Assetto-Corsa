-- HK Driving Test Exam System
-- Displays route guidance and tracks scoring during road test

local app = {
    name = "HK Exam System",
    author = "Hong Kong AC Project",
    version = "1.0.0",
    
    -- Exam state
    active = false,
    centre = nil,
    route_id = nil,
    route = nil,
    current_step = 1,
    
    -- Scoring
    score = 100,
    deductions = {},
    max_deductions = 100,  -- Fail if exceeds
    
    -- Position tracking
    last_position = nil,
    distance_traveled = 0,
    
    -- UI
    window = nil,
    visible = true,
}

-- Load route database
local routes_db = nil

local function load_routes()
    if routes_db then return routes_db end
    
    -- Try to load routes.lua
    local status, result = pcall(function()
        return dofile("apps/lua/hk_exam/routes.lua")
    end)
    
    if status and result then
        routes_db = result
        print(string.format("[HK Exam] Loaded %d routes", 
               (function() local c = 0; for _ in pairs(routes_db) do c = c + 1 end; return c end)()))
    else
        print("[HK Exam] Warning: Could not load routes.lua")
        routes_db = {}
    end
    
    return routes_db
end

-- Initialize exam
function app.init()
    print("[HK Exam] Initialized")
    app.window = ac.Window {
        name = "HK Exam System",
        width = 350,
        height = 500,
        position = ac.ImVec2(10, 10),
        visible = app.visible,
    }
end

-- Start exam
function app.start_exam(centre_id, route_id)
    app.centre = centre_id
    app.route_id = route_id
    app.current_step = 1
    app.score = 100
    app.deductions = {}
    app.active = true
    app.distance_traveled = 0
    app.last_position = nil
    
    -- Load route
    local routes = load_routes()
    app.route = routes[route_id]
    
    if app.route then
        print(string.format("[HK Exam] Started: %s / %s (%d steps)", 
               centre_id, route_id, #app.route.steps))
    else
        print(string.format("[HK Exam] Warning: Route %s not found", route_id))
    end
end

-- End exam
function app.end_exam()
    app.active = false
    local result = app.score >= 70 and "PASS" or "FAIL"
    print(string.format("[HK Exam] Ended: %s (Score: %d)", result, app.score))
    return result, app.score
end

-- Deduct points
function app.deduct(points, reason)
    if not app.active then return end
    
    app.score = math.max(0, app.score - points)
    table.insert(app.deductions, {
        step = app.current_step,
        points = points,
        reason = reason,
        time = ac.getSimTime(),
    })
    
    print(string.format("[HK Exam] -%d pts: %s (Score: %d)", points, reason, app.score))
end

-- Advance to next step
function app.next_step()
    if not app.active then return end
    
    app.current_step = app.current_step + 1
    print(string.format("[HK Exam] Step %d", app.current_step))
end

-- Update (called every frame)
function app.update(dt)
    if not app.active then return end
    
    local car = ac.getCar(0)
    if not car then return end
    
    local pos = car.position
    
    -- Calculate distance traveled
    if app.last_position then
        local dx = pos.x - app.last_position.x
        local dy = pos.y - app.last_position.y
        local dz = pos.z - app.last_position.z
        local dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        app.distance_traveled = app.distance_traveled + dist
    end
    app.last_position = {x = pos.x, y = pos.y, z = pos.z}
    
    -- Check speed limit (simplified: 50 km/h default)
    local speed_kmh = car.speed * 3.6
    if speed_kmh > 55 then  -- 5 km/h tolerance
        local overspeed = speed_kmh - 50
        if overspeed > 20 then
            app.deduct(10, string.format("超速 %.0f km/h", speed_kmh))
        elseif overspeed > 10 then
            app.deduct(5, string.format("超速 %.0f km/h", speed_kmh))
        end
    end
end

-- Render UI
function app.render()
    if not app.visible then return end
    
    if app.window then
        app.window:render(function()
            if not app.active then
                ac.drawText("考試系統", ac.ImVec2(10, 10), 0xffffffff)
                ac.drawText("按 [Start] 開始考試", ac.ImVec2(10, 40), 0xffaaaaaa)
                return
            end
            
            -- Header
            ac.drawText(string.format("考試進行中 - Step %d", app.current_step), 
                       ac.ImVec2(10, 10), 0xff00ff00)
            
            -- Score
            local score_color = app.score >= 70 and 0xff00ff00 or 0xffff0000
            ac.drawText(string.format("分數: %d / 100", app.score), 
                       ac.ImVec2(10, 40), score_color)
            
            -- Current instruction
            if app.route and app.route.steps then
                local step = app.route.steps[app.current_step]
                if step then
                    ac.drawText(string.format("指示 %d/%d:", 
                               app.current_step, #app.route.steps), 
                               ac.ImVec2(10, 70), 0xffaaaaaa)
                    ac.drawText(step.instruction, 
                               ac.ImVec2(10, 90), 0xffffffff)
                    
                    -- Turn indicator
                    local turn_color = 0xffffffff
                    if step.turn == "L" then turn_color = 0xff00ffff
                    elseif step.turn == "R" then turn_color = 0xffff00ff
                    elseif step.turn == "FINISH" then turn_color = 0xff00ff00
                    end
                    ac.drawText(string.format("轉向: %s", step.turn), 
                               ac.ImVec2(10, 110), turn_color)
                else
                    ac.drawText("路線完成!", ac.ImVec2(10, 70), 0xff00ff00)
                end
            else
                ac.drawText("指示: (未載入路線)", ac.ImVec2(10, 70), 0xffaaaaaa)
            end
            
            -- Deductions log
            local log_y = 140
            ac.drawText("扣分記錄:", ac.ImVec2(10, log_y), 0xffaaaaaa)
            log_y = log_y + 20
            for i = math.max(1, #app.deductions - 4), #app.deductions do
                local d = app.deductions[i]
                ac.drawText(string.format("- %d: -%d pts (%s)", 
                           d.step, d.points, d.reason), 
                           ac.ImVec2(10, log_y), 0xffff6666)
                log_y = log_y + 18
            end
            
            -- Distance
            ac.drawText(string.format("行駛距離: %.0f m", app.distance_traveled), 
                       ac.ImVec2(10, log_y + 10), 0xffaaaaaa)
        end)
    end
end

-- Register callbacks
ac.onCarUpdate(function(dt) app.update(dt) end)
ac.onRender(function() app.render() end)

-- Keyboard controls
ac.onKeyDown(function(key)
    -- F5: Start exam (default route)
    if key == ac.Keys.F5 and not app.active then
        app.start_exam("happy_valley", "happy_valley_1")
    -- F6: End exam
    elseif key == ac.Keys.F6 and app.active then
        app.end_exam()
    -- F7: Next step (manual advance)
    elseif key == ac.Keys.F7 and app.active then
        app.next_step()
    -- F8: Toggle visibility
    elseif key == ac.Keys.F8 then
        app.visible = not app.visible
        if app.window then
            app.window.visible = app.visible
        end
    end
end)

return app
