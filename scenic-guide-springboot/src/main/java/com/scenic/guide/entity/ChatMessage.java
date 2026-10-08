package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话消息
 */
@Data
@TableName("chat_messages")
public class ChatMessage {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("session_id")
    private String sessionId;

    private String role;

    private String content;

    @TableField("message_type")
    private String messageType;

    @TableField("audio_url")
    private String audioUrl;

    @TableField("video_url")
    private String videoUrl;

    private String emotion;

    @TableField("emotion_score")
    private Double emotionScore;

    @TableField(typeHandler = com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler.class, value = "rag_sources")
    private Object ragSources;

    @TableField("response_time")
    private Double responseTime;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
