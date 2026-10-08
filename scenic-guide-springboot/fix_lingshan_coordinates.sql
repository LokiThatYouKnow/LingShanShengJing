-- ============================================================================
-- 灵山胜境 — 坐标修正 V3（基于百度地图POI LocalSearch交叉验证）
-- 数据来源: Baidu Maps JS API LocalSearch, Wikipedia EN/ZH
-- 锚点 (WGS-84):
--   灵山大佛   (31.43194, 120.09139) — Wikipedia EN verified
--   灵山梵宫   (31.43028, 120.09750) — Wikipedia ZH verified
--   灵山大照壁 (31.42316, 120.09755) — Baidu POI verified
--   九龙灌浴   (31.42664, 120.09524) — Baidu POI verified
--   祥符禅寺   (31.42992, 120.09303) — Baidu POI verified
--
-- 关键发现: 中轴线从东南到西北倾斜（大照壁→大佛），经度从120.0975渐变到120.0914
-- 执行方式: mysql -u root -proot --default-character-set=utf8mb4 scenic_guide_ai < fix_lingshan_coordinates.sql
-- ============================================================================
USE scenic_guide_ai;

-- 1. 确保旧脏数据已停用（ID 1-5广州测试 + ID 18沙漠垃圾）
UPDATE spots SET is_active = 0 WHERE id IN (1, 2, 3, 4, 5, 18);

-- ===== 中轴线景点（南→北, 经度从120.0975递减到120.0914）=====

-- 1. 灵山大照壁 — 景区南端入口（百度POI验证）
UPDATE spots SET
  latitude = 31.42316, longitude = 120.09755,
  order_num = 1, category = '入口', icon = '🏛️'
WHERE id = 6 AND name = '灵山大照壁';

-- 2. 五明桥 — 大照壁北约67m, 跨玉带河
UPDATE spots SET
  latitude = 31.42376, longitude = 120.09715,
  order_num = 2, category = '桥梁', icon = '🌉'
WHERE id = 7 AND name = '五明桥';

-- 3. 佛足坛 — 五明桥北约60m
UPDATE spots SET
  latitude = 31.42428, longitude = 120.09681,
  order_num = 3, category = '朝圣', icon = '👣'
WHERE id = 8 AND name = '佛足坛';

-- 4. 五智门 — 佛足坛北约55m, 核心景区入口牌坊
UPDATE spots SET
  latitude = 31.42475, longitude = 120.09649,
  order_num = 4, category = '门户', icon = '⛩️'
WHERE id = 9 AND name = '五智门';

-- 5. 菩提大道 — 五智门北约80m, 长约180m的林荫步道
UPDATE spots SET
  latitude = 31.42543, longitude = 120.09604,
  order_num = 5, category = '步道', icon = '🌿'
WHERE id = 10 AND name = '菩提大道';

-- 6. 九龙灌浴 — 菩提大道北约140m, 核心广场, 大型动态群雕（百度POI验证）
UPDATE spots SET
  latitude = 31.42664, longitude = 120.09524,
  order_num = 6, category = '动态景观', icon = '🐉',
  open_time = '10:00-15:00', price = '免费'
WHERE id = 11 AND name = '九龙灌浴';

-- 7. 降魔浮雕 — 九龙灌浴北约90m, 大型紫铜浮雕壁画
UPDATE spots SET
  latitude = 31.42745, longitude = 120.09469,
  order_num = 7, category = '浮雕', icon = '🗿'
WHERE id = 12 AND name = '降魔浮雕';

-- 8. 阿育王柱 — 降魔北约80m, 花岗岩石柱
UPDATE spots SET
  latitude = 31.42818, longitude = 120.09420,
  order_num = 8, category = '地标', icon = '🗼'
WHERE id = 13 AND name = '阿育王柱';

-- 9. 百子戏弥勒 — 阿育王柱北约65m, 大型青铜群雕
UPDATE spots SET
  latitude = 31.42876, longitude = 120.09381,
  order_num = 9, category = '祈福', icon = '😊'
WHERE id = 14 AND name = '百子戏弥勒';

-- 10. 祥符禅寺 — 百子戏弥勒北约130m, 唐代古寺（百度POI验证）
UPDATE spots SET
  latitude = 31.42992, longitude = 120.09303,
  order_num = 10, category = '寺院', icon = '🏯',
  open_time = '08:00-17:00', price = '免费'
WHERE id = 15 AND name = '祥符禅寺';

-- 11. 灵山大佛 — 祥符禅寺北约225m(216级登云道), 88m青铜立佛（Wikipedia验证）
UPDATE spots SET
  latitude = 31.43194, longitude = 120.09139,
  order_num = 11, category = '核心地标', icon = '🗽',
  open_time = '08:00-17:00', price = '含在门票内'
WHERE id = 16 AND name = '灵山大佛';

-- ===== 东翼: 香水海区域 =====

-- 12. 灵山梵宫 — Wikipedia ZH验证
UPDATE spots SET
  latitude = 31.43028, longitude = 120.09750,
  order_num = 12, category = '艺术殿堂', icon = '🕌',
  open_time = '09:00-17:00', price = '含在门票内'
WHERE id = 17 AND name = '灵山梵宫';

-- 13. 佛教文化博览馆 (灵山大佛座基内)
UPDATE spots SET
  latitude = 31.43220, longitude = 120.09160,
  order_num = 13, category = '博览馆', icon = '📿',
  open_time = '08:00-17:00', price = '含在门票内'
WHERE id = 19 AND name = '佛教文化博览馆';

-- 14. 五印坛城 (香水海湖心岛)
UPDATE spots SET
  latitude = 31.42915, longitude = 120.09700,
  order_num = 14, category = '藏传佛教', icon = '🛕',
  open_time = '09:00-17:00', price = '含在门票内'
WHERE id = 20 AND name = '五印坛城';

-- 15. 曼飞龙塔 (香水海南岸)
UPDATE spots SET
  latitude = 31.42780, longitude = 120.09720,
  order_num = 15, category = '南传佛教', icon = '🕊️',
  open_time = '全天', price = '含在门票内'
WHERE id = 21 AND name = '曼飞龙塔';

-- 16. 无尽意斋 — 祥符禅寺西侧约150m
UPDATE spots SET
  latitude = 31.42450, longitude = 120.09120,
  order_num = 16, category = '名人纪念馆', icon = '🍵',
  open_time = '09:00-17:00', price = '免费'
WHERE id = 22 AND name = '无尽意斋';

-- 修正 scenics 表景区中心坐标
UPDATE scenics SET
  latitude = 31.42700,
  longitude = 120.09500
WHERE id = 1;

-- 验证查询
SELECT id, name, latitude, longitude, category, icon, is_active, order_num
FROM spots WHERE is_active = 1 ORDER BY order_num;
