package com.scenic.guide.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 知识库文档
 */
@Data
@TableName("knowledge_docs")
public class KnowledgeDoc {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;

    @TableField("file_name")
    private String fileName;

    @TableField("file_type")
    private String fileType;

    @TableField("file_path")
    private String filePath;

    @TableField("content_preview")
    private String contentPreview;

    @TableField("chunk_count")
    private Integer chunkCount;

    private String status;

    @TableField("error_msg")
    private String errorMsg;

    private String category;

    @TableField("uploaded_by")
    private Long uploadedBy;

    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
