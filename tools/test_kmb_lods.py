"""Exercise distance switching in real Lua with stub scene references (pip install lupa)."""
import unittest
from pathlib import Path

from lupa import LuaRuntime

from build_kmb_bus_lods import NATIVE_BANDS, native_config
import configparser

LUA = Path(__file__).with_name('kmb_traffic_lods.lua')


class LodTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            function model(name)
              return {name=name, visible=true,
                setVisible=function(self, v) self.visible=v end,
                findMeshes=function(self) return self end,
                ensureUniqueMaterials=function(self) end,
                setMaterialsFrom=function(self, other) self.paintFrom=other.name end}
            end
            function car(stock)
              local first=model('lod1')
              local c={definition={main='data/bus.kn5'}, _distanceSquared=0,
                _modelLod=first, _carPaintMeshes=first, loads=0}
              if not stock then
                c.definition.kmbLods={{file='bus_lod1.kn5',distance=80},
                  {file='bus_lod2.kn5',distance=140},
                  {file='bus_lod3.kn5',distance=250},
                  {file='bus_lod4.kn5',distance=450}}
              end
              c.root={loadKN5LOD=function(_, path, main)
                c.loads=c.loads+1
                if c.fail then return nil end
                assert(main=='data/bus.kn5')
                assert(path:match('^data/bus_lod[234].kn5$'))
                return model(path)
              end}
              return c
            end
        ''')
        self.module = self.lua.execute(LUA.read_text(encoding='utf-8'))
        self.car = self.lua.globals().car(False)

    def update(self, distance):
        self.car._distanceSquared = distance * distance
        self.module.update(self.car)

    def test_boundaries_both_directions_and_cached_reuse(self):
        for distance, expected in [(80, 1), (139.99, 1), (140, 2), (249.99, 2),
                                   (250, 3), (449.99, 3), (450, 4), (1000, 4),
                                   (300, 3), (200, 2), (90, 1), (500, 4)]:
            self.update(distance)
            self.assertEqual(self.car._kmbLODLevel or 1, expected)
            self.assertTrue(self.car._modelLod.visible)
            if self.car._kmbLODModels is not None:
                self.assertEqual(sum(bool(m.visible) for _, m in self.car._kmbLODModels.items()), 1)
        self.assertEqual(self.car.loads, 3)

    def test_full_detail_owns_visibility(self):
        self.car._fullLOD = self.lua.table()
        self.update(500)
        self.assertEqual(self.car.loads, 0)
        self.car._fullLOD = None
        self.update(500)
        self.assertEqual(self.car._kmbLODLevel, 4)

    def test_stock_car_is_unchanged(self):
        self.car = self.lua.globals().car(True)
        self.update(500)
        self.assertEqual(self.car.loads, 0)
        self.assertIsNone(self.car._kmbLODModels)

    def test_failed_load_keeps_previous_model_visible(self):
        self.car.fail = True
        self.update(500)
        self.assertEqual(self.car._modelLod.name, 'lod1')
        self.assertTrue(self.car._modelLod.visible)
        self.assertIsNone(self.car._kmbLODLevel)

    def test_native_bands_are_contiguous(self):
        cp = configparser.ConfigParser()
        cp.read_string(native_config('bus'))
        for i in range(5):
            self.assertEqual(cp.getint(f'LOD_{i}', 'IN'), NATIVE_BANDS[i])
            self.assertEqual(cp.getint(f'LOD_{i}', 'OUT'), NATIVE_BANDS[i+1])
        self.assertEqual(cp['LOD_0']['FILE'], 'bus.kn5')


if __name__ == '__main__':
    unittest.main()
