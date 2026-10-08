package com.scenic.guide.controller;

import com.scenic.guide.service.SadTalkerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * 数字人SadTalker本地渲染接口
 * 对接后端SadTalker推理服务
 */
@Slf4j
@RestController
@RequestMapping("/api/digital-human")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class DigitalHumanController {

    private final SadTalkerService sadTalkerService;

    /**
     * 获取数字人服务状态
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus() {
        Map<String, Object> status = sadTalkerService.getStatus();
        return ResponseEntity.ok(status);
    }

    /**
     * 上传音频并生成数字人视频
     * 
     * @param audioFile 音频文件 (WAV/MP3)
     * @param imageFile 形象图片 (PNG/JPG, 可选)
     * @param text      回复文本（用于字幕）
     * @param emotion   情感标签
     * @return sessionId 和视频URL
     */
    @PostMapping("/generate")
    public ResponseEntity<Map<String, Object>> generateVideo(
            @RequestParam("audio") MultipartFile audioFile,
            @RequestParam(value = "image", required = false) MultipartFile imageFile,
            @RequestParam(value = "text", required = false, defaultValue = "") String text,
            @RequestParam(value = "emotion", required = false, defaultValue = "neutral") String emotion
    ) {
        try {
            // 生成会话ID
            String sessionId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
            
            log.info("[DH] 生成视频请求: sessionId={}, audio={}, text={}", 
                    sessionId, audioFile.getOriginalFilename(), text);
            
            // 保存音频文件
            String audioPath = sadTalkerService.saveAudio(sessionId, audioFile.getInputStream());
            
            // 保存形象图片（如果有）
            String imagePath = null;
            if (imageFile != null && !imageFile.isEmpty()) {
                imagePath = sadTalkerService.saveImage(sessionId, imageFile.getInputStream());
            }
            
            // 调用SadTalker生成视频
            String videoUrl = sadTalkerService.generateVideo(sessionId, audioPath, imagePath, text, emotion);
            
            // 构建响应
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("sessionId", sessionId);
            response.put("videoUrl", videoUrl);
            response.put("text", text);
            response.put("emotion", emotion);
            response.put("timestamp", System.currentTimeMillis());
            
            return ResponseEntity.ok(response);
            
        } catch (IOException e) {
            log.error("[DH] 文件保存失败", e);
            return ResponseEntity.internalServerError().body(Map.of(
                    "success", false,
                    "error", "文件处理失败: " + e.getMessage()
            ));
        } catch (Exception e) {
            log.error("[DH] 视频生成失败", e);
            return ResponseEntity.internalServerError().body(Map.of(
                    "success", false,
                    "error", "视频生成失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 获取生成进度（用于长任务轮询）
     */
    @GetMapping("/progress/{sessionId}")
    public ResponseEntity<Map<String, Object>> getProgress(@PathVariable String sessionId) {
        Map<String, Object> progress = sadTalkerService.getProgress(sessionId);
        return ResponseEntity.ok(progress);
    }

    /**
     * WebSocket升级端点（可选，用于实时推送）
     */
    @GetMapping("/ws-info")
    public ResponseEntity<Map<String, Object>> getWsInfo() {
        Map<String, Object> info = new HashMap<>();
        info.put("wsUrl", "ws://localhost:8002");
        info.put("httpUrl", "http://localhost:8001");
        info.put("supported", true);
        return ResponseEntity.ok(info);
    }

    /**
     * 播放数字人（模拟流媒体，实际返回视频URL）
     */
    @PostMapping("/play")
    public ResponseEntity<Map<String, Object>> playDigitalHuman(
            @RequestBody Map<String, String> request
    ) {
        String sessionId = request.get("sessionId");
        
        if (sessionId == null || sessionId.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "sessionId不能为空"
            ));
        }
        
        // 获取视频URL
        String videoUrl = sadTalkerService.getVideoUrl(sessionId);
        
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("sessionId", sessionId);
        response.put("videoUrl", videoUrl);
        response.put("streamUrl", "/api/digital-human/stream/" + sessionId);
        
        return ResponseEntity.ok(response);
    }

    /**
     * 配置数字人参数
     */
    @GetMapping("/config")
    public ResponseEntity<Map<String, Object>> getConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("engine", "sadtalker");
        config.put("defaultAvatar", "/images/default_avatar.png");
        config.put("supportedEmotions", new String[]{"neutral", "happy", "sad", "excited"});
        config.put("maxAudioDuration", 60); // 秒
        config.put("outputFormat", "mp4");
        config.put("outputResolution", "512x512");
        return ResponseEntity.ok(config);
    }

    /**
     * 设置当前数字人形象
     */
    @PostMapping("/avatar")
    public ResponseEntity<Map<String, Object>> setAvatar(
            @RequestParam("image") MultipartFile imageFile
    ) {
        try {
            String avatarPath = sadTalkerService.saveDefaultAvatar(imageFile.getInputStream());
            
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "avatarPath", avatarPath
            ));
        } catch (IOException e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "success", false,
                    "error", e.getMessage()
            ));
        }
    }
}
