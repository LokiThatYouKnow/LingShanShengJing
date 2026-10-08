package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 数据分析事件
 */
@Data
@TableName("analytics_events")
public class AnalyticsEvent {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("event_type")
    private String eventType;

    @TableField("device_id")
    private String deviceId;

    private String platform;

    @TableField("session_id")
    private String sessionId;

    @TableField("spot_id")
    private Long spotId;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private Object data;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
