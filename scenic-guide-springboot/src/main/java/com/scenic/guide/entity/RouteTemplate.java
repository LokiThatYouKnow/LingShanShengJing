package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 游览路线模板
 */
@Data
@TableName("route_templates")
public class RouteTemplate {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String description;

    @TableField("scenic_id")
    private Long scenicId;

    @TableField("duration_hours")
    private Double durationHours;

    private String difficulty;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class, value = "spots_order")
    private Object spotsOrder;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private Object tags;

    @TableField("is_active")
    private Boolean isActive;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
