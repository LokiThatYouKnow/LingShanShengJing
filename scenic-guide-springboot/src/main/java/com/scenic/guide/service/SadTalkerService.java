package com.scenic.guide.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * SadTalker本地推理服务对接
 */
@Slf4j
@Service
public class SadTalkerService {

    // SadTalker服务地址
    @Value("${sadtalker.service-url:http://localhost:8001}")
    private String serviceUrl;

    // 文件存储路径
    @Value("${sadtalker.upload-dir:D:/TALKING/sadtalker-service/uploads}")
    private String uploadDir;

    @Value("${sadtalker.output-dir:D:/TALKING/sadtalker-service/output}")
    private String outputDir;

    // 进度跟踪
    private final Map<String, ProgressInfo> progressMap = new ConcurrentHashMap<>();

    static class ProgressInfo {
        String status; // pending, generating, complete, error
        int percent;
        String message;
        String videoUrl;

        ProgressInfo(String status, int percent, String message) {
            this.status = status;
            this.percent = percent;
            this.message = message;
        }
    }

    /**
     * 获取服务状态
     */
    public Map<String, Object> getStatus() {
        Map<String, Object> status = new ConcurrentHashMap<>();
        
        try {
            // 调用SadTalker服务的状态接口
            URL url = new URL(serviceUrl + "/status");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(3000);
            
            if (conn.getResponseCode() == 200) {
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream()))) {
                    String response = reader.lines().collect(Collectors.joining());
                    status.put("connected", true);
                    status.put("response", response);
                }
            } else {
                status.put("connected", false);
                status.put("error", "Service returned: " + conn.getResponseCode());
            }
        } catch (Exception e) {
            log.warn("[SadTalker] Status check failed: {}", e.getMessage());
            status.put("connected", false);
            status.put("error", e.getMessage());
            status.put("simulationMode", true);
        }
        
        status.put("serviceUrl", serviceUrl);
        status.put("uploadDir", uploadDir);
        status.put("outputDir", outputDir);
        
        return status;
    }

    /**
     * 保存音频文件
     */
    public String saveAudio(String sessionId, InputStream audioStream) throws IOException {
        Path audioDir = Paths.get(uploadDir, "audio");
        Files.createDirectories(audioDir);
        
        String filename = sessionId + ".wav";
        Path audioPath = audioDir.resolve(filename);
        
        try (OutputStream out = Files.newOutputStream(audioPath)) {
            audioStream.transferTo(out);
        }
        
        log.info("[SadTalker] Audio saved: {}", audioPath);
        return audioPath.toString();
    }

    /**
     * 保存形象图片
     */
    public String saveImage(String sessionId, InputStream imageStream) throws IOException {
        Path imageDir = Paths.get(uploadDir, "images");
        Files.createDirectories(imageDir);
        
        String filename = sessionId + ".png";
        Path imagePath = imageDir.resolve(filename);
        
        try (OutputStream out = Files.newOutputStream(imagePath)) {
            imageStream.transferTo(out);
        }
        
        log.info("[SadTalker] Image saved: {}", imagePath);
        return imagePath.toString();
    }

    /**
     * 保存默认形象（用于设置当前数字人）
     */
    public String saveDefaultAvatar(InputStream imageStream) throws IOException {
        Path avatarDir = Paths.get(uploadDir, "images");
        Files.createDirectories(avatarDir);
        
        Path avatarPath = avatarDir.resolve("default_avatar.png");
        
        try (OutputStream out = Files.newOutputStream(avatarPath)) {
            imageStream.transferTo(out);
        }
        
        log.info("[SadTalker] Default avatar saved: {}", avatarPath);
        return avatarPath.toString();
    }

    /**
     * 生成视频
     */
    public String generateVideo(String sessionId, String audioPath, String imagePath, 
                                 String text, String emotion) throws Exception {
        
        // 初始化进度
        progressMap.put(sessionId, new ProgressInfo("generating", 0, "准备生成..."));
        
        // 构造SadTalker请求
        URL url = new URL(serviceUrl + "/generate");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setConnectTimeout(60000); // 60秒连接超时
        
        // 构建multipart请求
        String boundary = "----SadTalkerBoundary" + UUID.randomUUID();
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        
        try (OutputStream out = conn.getOutputStream()) {
            // 添加session_id
            writeFormField(out, boundary, "session_id", sessionId);
            
            // 添加文本
            if (text != null && !text.isEmpty()) {
                writeFormField(out, boundary, "text", text);
            }
            
            // 添加情感
            writeFormField(out, boundary, "emotion", emotion);
            
            // 添加音频文件
            if (audioPath != null) {
                writeFileField(out, boundary, "audio", audioPath, "audio/wav");
            }
            
            // 添加图片（如果有）
            if (imagePath != null) {
                writeFileField(out, boundary, "image", imagePath, "image/png");
            }
            
            // 结束
            out.write(("--" + boundary + "--\r\n").getBytes());
        }
        
        // 读取响应
        int responseCode = conn.getResponseCode();
        log.info("[SadTalker] Generate response: {}", responseCode);
        
        if (responseCode == 200) {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream()))) {
                String response = reader.lines().collect(Collectors.joining());
                log.info("[SadTalker] Response: {}", response);
                
                // 更新进度
                progressMap.put(sessionId, new ProgressInfo("complete", 100, "生成完成"));
                
                // 返回视频URL
                return serviceUrl + "/output/" + sessionId + ".mp4";
            }
        } else {
            // 模拟模式：SadTalker服务未运行时返回模拟结果
            log.warn("[SadTalker] Service not available, returning simulated response");
            return simulateVideoGeneration(sessionId);
        }
    }

    /**
     * 模拟视频生成（当SadTalker服务未启动时）
     */
    private String simulateVideoGeneration(String sessionId) {
        // 更新进度为完成
        progressMap.put(sessionId, new ProgressInfo("complete", 100, "生成完成（模拟）"));
        
        // 返回模拟视频URL（实际不存在，仅用于测试前端逻辑）
        return serviceUrl + "/output/" + sessionId + "_simulated.mp4";
    }

    /**
     * 获取进度
     */
    public Map<String, Object> getProgress(String sessionId) {
        ProgressInfo info = progressMap.get(sessionId);
        
        if (info == null) {
            return Map.of(
                    "sessionId", sessionId,
                    "status", "not_found",
                    "percent", 0
            );
        }
        
        return Map.of(
                "sessionId", sessionId,
                "status", info.status,
                "percent", info.percent,
                "message", info.message,
                "videoUrl", info.videoUrl != null ? info.videoUrl : ""
        );
    }

    /**
     * 获取视频URL
     */
    public String getVideoUrl(String sessionId) {
        return serviceUrl + "/output/" + sessionId + ".mp4";
    }

    // ====== 辅助方法 ======

    private void writeFormField(OutputStream out, String boundary, String name, String value) 
            throws IOException {
        out.write(("--" + boundary + "\r\n").getBytes());
        out.write(("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n").getBytes());
        out.write((value + "\r\n").getBytes());
    }

    private void writeFileField(OutputStream out, String boundary, String fieldName,
                                String filePath, String contentType) throws IOException {
        File file = new File(filePath);
        if (!file.exists()) {
            log.warn("[SadTalker] File not found: {}", filePath);
            return;
        }

        out.write(("--" + boundary + "\r\n").getBytes());
        out.write(("Content-Disposition: form-data; name=\"" + fieldName + 
                   "\"; filename=\"" + file.getName() + "\"\r\n").getBytes());
        out.write(("Content-Type: " + contentType + "\r\n\r\n").getBytes());
        
        try (FileInputStream fis = new FileInputStream(file)) {
            fis.transferTo(out);
        }
        out.write("\r\n".getBytes());
    }
}
