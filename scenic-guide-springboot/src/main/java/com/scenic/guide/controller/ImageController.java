package com.scenic.guide.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 图片资源控制器 - 提供景点图片访问
 */
@RestController
@RequestMapping("/spot-images")
public class ImageController {

    @Value("${file.image-dir:d:/TalkingV2/图片}")
    private String imageDir;

    @GetMapping("/{filename:.+}")
    public ResponseEntity<Resource> getImage(@PathVariable String filename) throws IOException {
        // URL解码文件名（处理中文）
        String decodedFilename = URLDecoder.decode(filename, StandardCharsets.UTF_8);

        // 构建安全路径
        Path basePath = Paths.get(imageDir).toAbsolutePath().normalize();
        Path imagePath = basePath.resolve(decodedFilename).normalize();

        // 安全检查：防止路径遍历攻击
        if (!imagePath.startsWith(basePath)) {
            return ResponseEntity.badRequest().build();
        }

        Resource resource = new FileSystemResource(imagePath);
        if (!resource.exists() || !resource.isReadable()) {
            return ResponseEntity.notFound().build();
        }

        // 根据文件扩展名设置Content-Type
        String lower = decodedFilename.toLowerCase();
        MediaType mediaType;
        if (lower.endsWith(".png")) {
            mediaType = MediaType.IMAGE_PNG;
        } else if (lower.endsWith(".gif")) {
            mediaType = MediaType.IMAGE_GIF;
        } else if (lower.endsWith(".webp")) {
            mediaType = MediaType.valueOf("image/webp");
        } else {
            mediaType = MediaType.IMAGE_JPEG;
        }

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, mediaType.toString())
                .body(resource);
    }
}
