package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 景区信息
 */
@Data
@TableName("scenics")
public class Scenic {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String description;

    private String address;

    private Double latitude;

    private Double longitude;

    @TableField("open_time")
    private String openTime;

    @TableField("ticket_price")
    private String ticketPrice;

    private String phone;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class)
    private Object images;

    @TableField("is_active")
    private Boolean isActive;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
