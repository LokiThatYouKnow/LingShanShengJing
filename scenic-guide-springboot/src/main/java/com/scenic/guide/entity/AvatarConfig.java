package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 数字人形象配置
 */
@Data
@TableName("avatar_configs")
public class AvatarConfig {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String description;

    @TableField("image_url")
    private String imageUrl;

    @TableField("voice_name")
    private String voiceName;

    @TableField("voice_rate")
    private String voiceRate;

    @TableField("voice_pitch")
    private String voicePitch;

    @TableField("welcome_text")
    private String welcomeText;

    @TableField("is_default")
    private Boolean isDefault;

    @TableField("is_active")
    private Boolean isActive;

    @TableField("sadtalker_enabled")
    private Boolean sadtalkerEnabled;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
