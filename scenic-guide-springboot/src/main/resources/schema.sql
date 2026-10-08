-- 景区导览AI数字人系统 - 数据库初始化脚本
-- Spring Boot 版本 (v2.0)

CREATE DATABASE IF NOT EXISTS scenic_guide_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE scenic_guide_ai;

-- 管理员用户表
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL UNIQUE,
  `email` varchar(100) DEFAULT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `role` varchar(20) DEFAULT 'admin',
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员用户';

-- 游客信息表
CREATE TABLE IF NOT EXISTS `tourists` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `device_id` varchar(100) NOT NULL UNIQUE,
  `nickname` varchar(50) DEFAULT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `visit_count` int DEFAULT 0,
  `last_visit` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='游客信息';

-- 景区信息表
CREATE TABLE IF NOT EXISTS `scenics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `open_time` varchar(100) DEFAULT NULL,
  `ticket_price` varchar(100) DEFAULT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `images` json DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='景区信息';

-- 景点信息表
CREATE TABLE IF NOT EXISTS `spots` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `scenic_id` bigint DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `guide_text` text DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `trigger_radius` double DEFAULT 50.0,
  `order_num` int DEFAULT 0,
  `duration_minutes` int DEFAULT 5,
  `category` varchar(50) DEFAULT NULL,
  `icon` varchar(20) DEFAULT NULL COMMENT 'emoji图标',
  `open_time` varchar(100) DEFAULT '全天' COMMENT '开放时间',
  `price` varchar(50) DEFAULT '免费' COMMENT '票价',
  `images` json DEFAULT NULL,
  `audio_url` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_scenic_id` (`scenic_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='景点信息';

-- 对话会话表
CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) NOT NULL UNIQUE,
  `tourist_id` bigint DEFAULT NULL,
  `device_id` varchar(100) DEFAULT NULL,
  `platform` varchar(20) DEFAULT 'app',
  `start_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `end_time` datetime DEFAULT NULL,
  `message_count` int DEFAULT 0,
  `satisfaction_score` double DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话会话';

-- 对话消息表
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) DEFAULT NULL,
  `role` varchar(10) NOT NULL,
  `content` text NOT NULL,
  `message_type` varchar(20) DEFAULT 'text',
  `audio_url` varchar(255) DEFAULT NULL,
  `video_url` varchar(255) DEFAULT NULL,
  `emotion` varchar(20) DEFAULT NULL,
  `emotion_score` double DEFAULT NULL,
  `rag_sources` json DEFAULT NULL,
  `response_time` double DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话消息';

-- 知识库文档表
CREATE TABLE IF NOT EXISTS `knowledge_docs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `file_type` varchar(20) DEFAULT NULL,
  `file_path` varchar(500) DEFAULT NULL,
  `content_preview` text DEFAULT NULL,
  `chunk_count` int DEFAULT 0,
  `status` varchar(20) DEFAULT 'pending',
  `error_msg` text DEFAULT NULL,
  `category` varchar(50) DEFAULT 'general',
  `uploaded_by` bigint DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档';

-- FAQ 表
CREATE TABLE IF NOT EXISTS `faqs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `question` text NOT NULL,
  `answer` text NOT NULL,
  `category` varchar(50) DEFAULT 'general',
  `hit_count` int DEFAULT 0,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常见问答';

-- 数字人配置表
CREATE TABLE IF NOT EXISTS `avatar_configs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `image_url` varchar(255) NOT NULL,
  `voice_name` varchar(100) DEFAULT NULL,
  `voice_rate` varchar(20) DEFAULT '+0%',
  `voice_pitch` varchar(20) DEFAULT '+0Hz',
  `welcome_text` text DEFAULT NULL,
  `is_default` tinyint(1) DEFAULT 0,
  `is_active` tinyint(1) DEFAULT 1,
  `sadtalker_enabled` tinyint(1) DEFAULT 1 COMMENT 'SadTalker视频生成开关',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数字人配置';

-- 数据分析事件表
CREATE TABLE IF NOT EXISTS `analytics_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_type` varchar(50) NOT NULL,
  `device_id` varchar(100) DEFAULT NULL,
  `platform` varchar(20) DEFAULT NULL,
  `session_id` varchar(100) DEFAULT NULL,
  `spot_id` bigint DEFAULT NULL,
  `data` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据分析事件';

-- 路线模板表
CREATE TABLE IF NOT EXISTS `route_templates` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `scenic_id` bigint DEFAULT NULL,
  `duration_hours` double DEFAULT NULL,
  `difficulty` varchar(20) DEFAULT 'easy',
  `spots_order` json DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='游览路线模板';

-- ===================== 初始数据 =====================

-- 默认管理员（密码: admin123）
-- BCrypt hash of "admin123"
INSERT IGNORE INTO `users` (`username`, `email`, `hashed_password`, `role`, `is_active`)
VALUES ('admin', 'admin@scenic.com',
        '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAd6a5NbN4N1dqDmM3HVV5DG7Ktu',
        'super_admin', 1);

-- 默认景区
INSERT IGNORE INTO `scenics` (`id`, `name`, `description`, `address`, `latitude`, `longitude`,
                               `open_time`, `ticket_price`, `phone`, `is_active`)
VALUES (1, '云山风景区', '国家AAAAA级旅游景区，集自然山水与人文景观于一体，是市民休闲游览的好去处。',
        '广东省广州市白云区云山大道', 23.1781, 113.2682,
        '08:00-19:00（旺季）/ 08:30-18:30（淡季）',
        '成人票80元 | 学生票40元 | 老人/残疾人免票',
        '020-12345678', 1);

-- 默认景点
INSERT IGNORE INTO `spots` (`id`, `scenic_id`, `name`, `description`, `guide_text`, `latitude`,
                             `longitude`, `trigger_radius`, `order_num`, `duration_minutes`,
                             `category`, `icon`, `open_time`, `price`, `is_active`)
VALUES
(1, 1, '景区大门', '景区主入口，是游览的起点。建筑风格融合了古典与现代元素。',
 '欢迎来到云山风景区！这里是景区大门，建于1985年，承载了无数游客的美好回忆。入口处的石雕狮子是景区的标志性建筑，象征着吉祥与守护。',
 23.1771, 113.2672, 50.0, 1, 5, '入口', '🚪', '07:00-18:00', '免费', 1),

(2, 1, '观景台', '海拔320米的高峰观景台，可俯瞰整个城市景观。',
 '您现在来到了观景台，这里是景区制高点，海拔320米。晴天时，可以看到城市全景和远处的海湾。每到日落时分，这里聚集了大批摄影爱好者，记录城市最美的光影时刻。',
 23.1881, 113.2782, 80.0, 2, 15, '观景', '🔭', '08:00-18:00', '免费', 1),

(3, 1, '古树林', '百年古树保护区，有超过50棵树龄逾百年的参天大树。',
 '古树林是景区的生态瑰宝，这里有50多棵树龄超过百年的珍稀古树。最老的一棵榕树已有380年历史，树干需要十人合抱。林间小道蜿蜒幽静，空气清新，负氧离子含量是城市的15倍。',
 23.1841, 113.2712, 60.0, 3, 20, '自然', '🌳', '全天', '免费', 1),

(4, 1, '文化广场', '景区中心广场，定期举办民俗表演和文化活动。',
 '文化广场是景区的文化核心，广场中央的大型浮雕记载了本地区千年的历史变迁。每逢节假日，这里会举办精彩的民俗表演，包括舞狮、粤剧清唱等传统节目，让游客感受浓厚的岭南文化。',
 23.1791, 113.2702, 70.0, 4, 15, '文化', '🎭', '09:00-17:00', '免费', 1),

(5, 1, '山顶寺庙', '建于明朝的古刹，香火鼎盛，是祈福求愿的圣地。',
 '山顶寺庙始建于明朝万历年间，距今已有400余年历史。寺内供奉的主神是当地保护神，每年春节和观音诞，前来朝拜的信众多达数万人。寺庙的建筑采用传统岭南风格，飞檐翘角，金碧辉煌。',
 23.1901, 113.2742, 60.0, 5, 20, '人文', '🛕', '08:00-17:30', '免费', 1);

-- 默认数字人配置
INSERT IGNORE INTO `avatar_configs` (`id`, `name`, `description`, `image_url`, `voice_name`,
                                      `voice_rate`, `voice_pitch`, `welcome_text`, `is_default`, `is_active`, `sadtalker_enabled`)
VALUES
(1, '小云（漫画风）', '活泼可爱的动漫风格导游小姐姐',
 '/static/avatar/avatar_cartoon.png', 'zh-CN-XiaoxiaoNeural',
 '+0%', '+0Hz',
 '您好！我是景区智能导游小云，很高兴为您服务！您可以问我关于景区的任何问题，我会尽力为您解答。请问您想了解什么呢？',
 1, 1, 1),

(2, '小智（Q版）', '呆萌Q版风格导游形象',
 '/static/avatar/avatar_q.png', 'zh-CN-XiaohanNeural',
 '+0%', '+0Hz',
 '嗨！我是景区导游小智，来自云山风景区！今天天气不错，非常适合游览。有什么我可以帮到您的吗？',
 0, 1, 1),

(3, '小灵（数字人）', 'SadTalker高质量视频数字人导览',
 '/static/avatar/avatar_sadtalker.png', 'zh-CN-XiaoxiaoNeural',
 '+0%', '+0Hz',
 '您好！欢迎来到灵山胜境，我是AI导览助手小灵，请问有什么可以帮您？',
 0, 1, 1);

-- 示例 FAQ
INSERT IGNORE INTO `faqs` (`question`, `answer`, `category`, `hit_count`, `is_active`)
VALUES
('景区开放时间是什么时候？', '旺季（4月-10月）：08:00-19:00，淡季（11月-3月）：08:30-18:30。最晚入场时间为闭园前1小时。', 'basic', 156, 1),
('门票价格是多少？', '成人票80元，学生票（凭学生证）40元，60岁以上老人及残疾人凭证免票，儿童（身高1.2米以下）免票。', 'ticket', 234, 1),
('景区内有哪些餐厅？', '景区内有3家餐厅：山顶观景餐厅（提供粤菜）、文化广场快餐厅（快餐小吃）和古树林茶馆（特色茶点）。建议提前预订山顶餐厅。', 'food', 89, 1),
('怎么去景区？', '公交：乘坐36路、52路、168路至"云山景区"站下车；地铁：2号线至"云山站"，步行约15分钟；自驾：导航至景区停车场，停车费10元/小时。', 'traffic', 178, 1),
('景区有停车场吗？', '景区设有两个停车场：南门停车场（500个车位）和北门停车场（300个车位）。费用：小型车10元/小时，全天最高收费50元。', 'parking', 67, 1);

-- 示例路线模板
INSERT IGNORE INTO `route_templates` (`name`, `description`, `scenic_id`, `duration_hours`,
                                       `difficulty`, `spots_order`, `tags`, `is_active`)
VALUES
('经典全览路线', '游览景区所有主要景点，适合时间充裕的游客', 1, 4.0, 'easy',
 '[1, 2, 3, 4, 5]', '["经典", "全览", "家庭"]', 1),
('快速游览路线', '1.5小时精华路线，适合时间紧张的游客', 1, 1.5, 'easy',
 '[1, 4, 2]', '["快速", "精华"]', 1),
('登山健身路线', '挑战登顶观景台，适合有一定体力的游客', 1, 3.0, 'medium',
 '[1, 3, 2, 5]', '["登山", "健身", "摄影"]', 1);
