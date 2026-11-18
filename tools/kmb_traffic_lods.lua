-- Optional distance LODs for KMB definitions. Stock traffic keeps its two LODs.
local KmbBusLODs = {}

function KmbBusLODs.update(car)
  local levels = car.definition.kmbLods
  if not levels or car._fullLOD ~= nil then return end
  local selected = 1
  for i = 2, #levels do
    if car._distanceSquared >= levels[i].distance ^ 2 then selected = i end
  end
  if selected == (car._kmbLODLevel or 1) then return end

  local models = car._kmbLODModels
  if not models then
    models = { [1] = car._modelLod }
    car._kmbLODModels = models
  end
  local model = models[selected]
  local paint
  if not model then
    local directory = car.definition.main:match('^(.*/)') or ''
    model = car.root:loadKN5LOD(directory .. levels[selected].file, car.definition.main)
    if not model then return end
    model:setVisible(false)
    paint = model:findMeshes('shader:ksPerPixelMultiMap_damage_dirt')
    paint:ensureUniqueMaterials()
    paint:setMaterialsFrom(car._carPaintMeshes)
    models[selected] = model
  else
    paint = model:findMeshes('shader:ksPerPixelMultiMap_damage_dirt')
    paint:setMaterialsFrom(car._carPaintMeshes)
  end
  car._modelLod:setVisible(false)
  car._modelLod = model
  car._carPaintMeshes = paint
  car._kmbLODLevel = selected
  model:setVisible(true)
end

return KmbBusLODs
