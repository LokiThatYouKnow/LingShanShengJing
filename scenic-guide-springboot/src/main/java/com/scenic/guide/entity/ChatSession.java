package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话会话
 */
@Data
@TableName("chat_sessions")
public class ChatSession {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("session_id")
    private String sessionId;

    @TableField("tourist_id")
    private Long touristId;

    @TableField("device_id")
    private String deviceId;

    private String platform;

    @TableField("start_time")
    private LocalDateTime startTime;

    @TableField("end_time")
    private LocalDateTime endTime;

    @TableField("message_count")
    private Integer messageCount;

    @TableField("satisfaction_score")
    private Double satisfactionScore;

    @TableField("is_active")
    private Boolean isActive;
}
