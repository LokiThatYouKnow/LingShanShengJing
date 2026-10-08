package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 景点信息
 */
@Data
@TableName("spots")
public class Spot {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("scenic_id")
    private Long scenicId;

    private String name;

    private String description;

    @TableField("guide_text")
    private String guideText;

    private Double latitude;

    private Double longitude;

    @TableField("trigger_radius")
    private Double triggerRadius;

    @TableField("order_num")
    private Integer orderNum;

    @TableField("duration_minutes")
    private Integer durationMinutes;

    private String category;

    /** 景点图标（emoji） */
    private String icon;

    /** 开放时间，如 "08:00-17:30" */
    @TableField("open_time")
    private String openTime;

    /** 票价，如 "免费" 或 "¥20" */
    private String price;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private Object images;

    @TableField("audio_url")
    private String audioUrl;

    @TableField("is_active")
    private Boolean isActive;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
