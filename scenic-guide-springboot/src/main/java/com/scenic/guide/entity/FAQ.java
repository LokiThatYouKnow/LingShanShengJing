package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 常见问答 FAQ
 */
@Data
@TableName("faqs")
public class FAQ {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String question;

    private String answer;

    private String category;

    @TableField("hit_count")
    private Integer hitCount;

    @TableField("is_active")
    private Boolean isActive;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
