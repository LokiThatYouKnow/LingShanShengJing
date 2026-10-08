/**
 * 无锡市灵山胜境 — 景点数据集 V4
 * 包含16个景点，坐标基于百度地图POI + Wikipedia交叉验证修正
 *
 * 坐标说明：
 * - lat/lng: WGS-84 GPS坐标（已矫正，用于百度地图精确定位）
 * - mapX/mapY: 2D SVG地图坐标（基于GPS位置线性映射：
 *   mapY = 750 - (lat - 31.4225) * 72000
 *   mapX 以主轴线（大照壁→大佛，SE→NW）为基准，东翼右偏、西侧左偏）
 *
 * 真实布局（main axis SE→NW）：
 *   中轴线大照壁(lng 120.09755)→大佛(lng 120.09139)，向东偏约52px
 *   东翼(梵宫/五印坛城/曼飞龙塔)在主轴线东侧香水海区域
 *   无尽意斋在主轴线西侧山林间，mapX最左(80)
 *   佛教文化博览馆在大佛座基内，紧邻大佛
 */
export const LINGSHAN_SPOTS = [
  // ==================== 主轴线（南→北，经度从东向西递减）====================
  {
    id: 1,
    name: '灵山大照壁',
    icon: '🏛️',
    description: '全长39.8米，高7米，被誉为"华夏第一壁"。正面浮雕"灵山胜会"，背面刻"唐僧赐禅小灵山图"。赵朴初先生题写"灵山胜境"。',
    openTime: '全天',
    price: '免费',
    distance: 50,
    image: '/spot-images/灵山大照壁.jpg?t=2',
    lat: 31.42316,
    lng: 120.09755,
    mapX: 290,
    mapY: 738,
    location: '景区入口处，面朝太湖',
    category: '入口'
  },
  {
    id: 2,
    name: '五明桥',
    icon: '🌉',
    description: '五座汉白玉石拱桥横跨玉带河，分别代表声明、工巧明、医方明、因明、内明五种智慧。桥身雕刻精美莲花图案。',
    openTime: '全天',
    price: '免费',
    distance: 100,
    image: '/spot-images/五明桥.jpg?t=2',
    lat: 31.42376,
    lng: 120.09715,
    mapX: 288,
    mapY: 695,
    location: '大照壁北侧，横跨玉带河',
    category: '桥梁'
  },
  {
    id: 3,
    name: '佛足坛',
    icon: '👣',
    description: '复刻佛祖释迦牟尼真身脚印，长1.2米、宽0.6米，足心刻有32种吉祥图案。安放在莲花宝座之上供信众瞻仰。',
    openTime: '全天',
    price: '免费',
    distance: 150,
    image: '/spot-images/佛足坛.png',
    lat: 31.42428,
    lng: 120.09681,
    mapX: 286,
    mapY: 658,
    location: '五明桥北侧，菩提大道起点',
    category: '朝圣'
  },
  {
    id: 4,
    name: '五智门',
    icon: '⛩️',
    description: '高16.8米的汉白玉石牌坊，五门象征五方五佛。门楣镌刻"布施、持戒、忍辱、精进、禅定、般若"六度法门。',
    openTime: '全天',
    price: '免费',
    distance: 200,
    image: '/spot-images/五智门.jpeg',
    lat: 31.42475,
    lng: 120.09649,
    mapX: 284,
    mapY: 620,
    location: '佛足坛北侧，核心景区入口',
    category: '门户'
  },
  {
    id: 5,
    name: '菩提大道',
    icon: '🌿',
    description: '两侧种植银杏树，形成天然禅意拱廊步道。全长约180米，春季绿荫如盖，秋末金叶铺地，美景如画。',
    openTime: '全天',
    price: '免费',
    distance: 280,
    image: '/spot-images/菩提大道.jpg',
    lat: 31.42543,
    lng: 120.09604,
    mapX: 280,
    mapY: 566,
    location: '五智门北侧，通向九龙灌浴',
    category: '步道'
  },
  {
    id: 6,
    name: '九龙灌浴',
    icon: '🐉',
    description: '"花开见佛，九龙沐浴"——高27.5米大型音乐动态群雕。莲花绽放，太子佛升起，九条巨龙口吐净水30米高。每日10:00、11:30、14:45、16:40开演。',
    openTime: '10:00-15:00',
    price: '免费',
    distance: 350,
    image: '/spot-images/九龙灌浴.jpeg',
    lat: 31.42664,
    lng: 120.09524,
    mapX: 274,
    mapY: 472,
    location: '菩提大道北端，中轴线核心广场',
    category: '动态景观'
  },
  {
    id: 7,
    name: '降魔浮雕',
    icon: '🗿',
    description: '长26米的巨型紫铜浮雕壁画，以精湛的技艺再现佛陀六年苦修、降魔成道的伟大历程。画面气势恢宏，人物栩栩如生。',
    openTime: '全天',
    price: '免费',
    distance: 400,
    image: '/spot-images/降魔浮雕.jpeg',
    lat: 31.42745,
    lng: 120.09469,
    mapX: 268,
    mapY: 408,
    location: '九龙灌浴北侧，阿育王柱前方',
    category: '浮雕'
  },
  {
    id: 8,
    name: '阿育王柱',
    icon: '🗼',
    description: '高16.9米，由整块花岗岩雕琢而成，柱身刻有梵文经文。纪念古印度阿育王弘扬佛法、派遣使者东传佛教的伟大历史。',
    openTime: '全天',
    price: '免费',
    distance: 450,
    image: '/spot-images/阿育王柱.jpeg',
    lat: 31.42818,
    lng: 120.09420,
    mapX: 262,
    mapY: 350,
    location: '降魔浮雕北侧，蔬食馆旁',
    category: '地标'
  },
  {
    id: 9,
    name: '百子戏弥勒',
    icon: '😊',
    description: '大型青铜群雕，塑造了弥勒菩萨被百名孩童围绕嬉戏的欢乐场景。造型生动活泼，寓意多子多福、欢乐吉祥。"摸摸弥勒脚，快乐没烦恼"。',
    openTime: '全天',
    price: '免费',
    distance: 500,
    image: '/spot-images/百子戏弥勒.jpg',
    lat: 31.42876,
    lng: 120.09381,
    mapX: 256,
    mapY: 305,
    location: '阿育王柱与祥符禅寺之间',
    category: '祈福'
  },
  {
    id: 10,
    name: '祥符禅寺',
    icon: '🏯',
    description: '始建于唐贞观年间（公元627年），江南千年禅宗祖庭。寺内古银杏树龄约1400年，梵音缭绕。可拍摄"佛在佛中"经典构图。',
    openTime: '08:00-17:00',
    price: '免费',
    distance: 600,
    image: '/spot-images/祥符禅寺.jpeg',
    lat: 31.42992,
    lng: 120.09303,
    mapX: 248,
    mapY: 215,
    location: '中轴核心，灵山大佛基座正南方',
    category: '寺院'
  },
  {
    id: 11,
    name: '灵山大佛',
    icon: '🗽',
    description: '通高88米（含基座101.5米），耗铜725吨，世界最大青铜立佛像。面朝太湖，背靠秦履峰，左手"与愿印"赐福，右手"施无畏印"除苦。登216级登云道可达佛座，"抱佛脚"祈福。',
    openTime: '08:00-17:00',
    price: '含在门票内',
    distance: 700,
    image: '/spot-images/灵山大佛.jpeg',
    lat: 31.43194,
    lng: 120.09139,
    mapX: 238,
    mapY: 48,
    location: '祥符禅寺北侧，秦履峰南侧，景区最高点',
    category: '核心地标'
  },

  // ==================== 东翼：香水海佛教文化体验区 ====================
  {
    id: 12,
    name: '灵山梵宫',
    icon: '🕌',
    description: '被誉为"东方卢浮宫"，宽150米，深180米，造价18亿。穹顶壁画《华藏世界》1500平方米，集木雕、琉璃、油画等艺术瑰宝于一体。《吉祥颂》大型音乐史诗每日上演。',
    openTime: '09:00-17:00',
    price: '含在门票内',
    distance: 800,
    image: '/spot-images/灵山梵宫.jpeg',
    lat: 31.43028,
    lng: 120.09750,
    mapX: 345,
    mapY: 195,
    location: '中轴线东侧，香水海北岸，东翼核心',
    category: '艺术殿堂'
  },
  {
    id: 13,
    name: '五印坛城',
    icon: '🛕',
    description: '藏式建筑"小布达拉宫"，白墙红边金顶，坐落于香水海中央圆岛。高31.55米共6层，展示唐卡、坛城沙画、转经筒。4F观景台可同时拍摄大佛+梵宫。',
    openTime: '09:00-17:00',
    price: '含在门票内',
    distance: 850,
    image: '',
    lat: 31.42915,
    lng: 120.09700,
    mapX: 340,
    mapY: 278,
    location: '香水海中央圆岛上，梵宫南侧',
    category: '藏传佛教'
  },
  {
    id: 14,
    name: '曼飞龙塔',
    icon: '🕊️',
    description: '复刻云南西双版纳曼飞龙白塔（始建于1204年），南传佛教标志性建筑。一主塔(16.29m)+八小塔(9.1m)，洁白塔身如竹笋般在阳光下熠熠生辉。',
    openTime: '全天',
    price: '含在门票内',
    distance: 820,
    image: '',
    lat: 31.42780,
    lng: 120.09720,
    mapX: 336,
    mapY: 380,
    location: '香水海东南岸，曼飞龙塔广场',
    category: '南传佛教'
  },

  // ==================== 西侧 ====================
  {
    id: 15,
    name: '佛教文化博览馆',
    icon: '📿',
    description: '位于灵山大佛座基内，三层约10000平方米展馆，系统展示佛教历史、文化、艺术。收藏金丝楠木雕刻"五百罗汉堂"等珍贵文物。',
    openTime: '08:00-17:00',
    price: '含在门票内',
    distance: 700,
    image: '',
    lat: 31.43220,
    lng: 120.09160,
    mapX: 242,
    mapY: 28,
    location: '灵山大佛座基内（共三层：博览馆→随喜堂→万佛殿）',
    category: '博览馆'
  },
  {
    id: 16,
    name: '无尽意斋',
    icon: '🍵',
    description: '赵朴初先生北京故居复刻，约600平方米四合院。院内竹林掩映，陈列赵朴老照片、书法、信件。可品茶休憩，感受一代佛教领袖的精神世界。',
    openTime: '09:00-17:00',
    price: '免费',
    distance: 750,
    image: '',
    lat: 31.42450,
    lng: 120.09120,
    mapX: 80,
    mapY: 640,
    location: '祥符禅寺西侧，杏坛广场旁山林间',
    category: '名人纪念馆'
  }
]

/**
 * 景区GPS边界（用于GPS→2D坐标映射）
 */
export const LINGSHAN_BOUNDS = {
  minLng: 120.0890,
  maxLng: 120.1000,
  minLat: 31.4220,
  maxLat: 31.4335
}

/**
 * 灵山景区中心坐标（用于百度地图初始定位）
 */
export const LINGSHAN_CENTER = {
  lng: 120.0945,
  lat: 31.4275
}

/**
 * 游览路线（景点ID序列，用于2D地图连线）
 */
export const TOUR_ROUTES = {
  main: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],      // 中轴线主路线（11个景点，南→北）
  east: [6, 14, 13, 12],                               // 东翼文化路线：九龙灌浴→曼飞龙塔→五印坛城→梵宫
  west: [10, 16],                                       // 无尽意斋支线：祥符禅寺→无尽意斋
  museum: [11, 15]                                      // 博览馆支线：灵山大佛→佛教文化博览馆
}
