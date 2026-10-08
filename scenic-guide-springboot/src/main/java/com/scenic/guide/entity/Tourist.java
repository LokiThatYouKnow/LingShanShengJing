package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 游客信息
 */
@Data
@TableName("tourists")
public class Tourist {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("device_id")
    private String deviceId;

    private String nickname;

    @TableField("avatar_url")
    private String avatarUrl;

    @TableField("visit_count")
    private Integer visitCount;

    @TableField("last_visit")
    private LocalDateTime lastVisit;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
