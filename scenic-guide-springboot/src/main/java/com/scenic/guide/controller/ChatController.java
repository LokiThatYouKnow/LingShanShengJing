package com.scenic.guide.controller;

import com.scenic.guide.common.result.Result;
import com.scenic.guide.service.LlmService;
import com.scenic.guide.service.SadTalkerService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

/**
 * AI 对话 Controller
 *
 * 完整对话链路（实时对话模式）：
 *   前端 → /chat/message → LLM（智谱云）→ SadTalker视频生成 → 返回 answer + audioUrl + videoUrl
 *
 * SadTalker 需要：
 *   - 音频文件（WAV）
 *   - 形象图片（PNG/JPG，可选，有默认图）
 *
 * 当前使用测试音频文件，待 TTS 服务接入后替换真实音频路径。
 */
@Api(tags = "AI对话")
@Slf4j
@RestController
@RequestMapping("/chat")
@RequiredArgsConstructor
public class ChatController {

    private final LlmService llmService;
    private final SadTalkerService sadTalkerService;

    @Value("${ai.enabled:false}")
    private boolean aiEnabled;

    /**
     * 发送文本消息（实时对话模式 → 返回文字 + 音频 + SadTalker视频）
     *
     * @param request { message, sessionId, history? }
     * @return { sessionId, answer, audioUrl, videoUrl, emotion, ragSources }
     */
    @ApiOperation("发送文本消息（实时对话 → 数字人视频）")
    @PostMapping("/message")
    public ResponseEntity<?> sendMessage(@RequestBody Map<String, Object> request) {
        String message = (String) request.getOrDefault("message", "");
        String sessionId = (String) request.getOrDefault("sessionId",
                UUID.randomUUID().toString().replace("-", "").substring(0, 16));

        @SuppressWarnings("unchecked")
        List<Map<String, String>> history = (List<Map<String, String>>) request.get("history");

        log.info("[Chat] sessionId={}, message={}", sessionId, message);

        try {
            // Step 1: 调用 LLM 获取回复
            String answer = llmService.chat(message, history);
            String emotion = llmService.detectEmotion(answer);
            log.info("[Chat] LLM 回复: {} (emotion={})", answer.substring(0, Math.min(30, answer.length())), emotion);

            // Step 2: 调用 Python TTS 服务生成真实语音
            String audioUrl = null;
            String ttsAudioPath = null;
            try {
                ttsAudioPath = callTTSService(answer, sessionId);
                if (ttsAudioPath != null) {
                    audioUrl = "/static/audio/" + sessionId + ".mp3";
                }
                log.info("[Chat] TTS 音频生成成功: {}", ttsAudioPath);
            } catch (Exception e) {
                log.warn("[Chat] TTS 生成失败，使用静默模式: {}", e.getMessage());
            }

            // Step 3: 生成 SadTalker 视频（使用真实的 TTS 音频）
            String videoUrl = null;
            String videoError = null;
            try {
                log.info("[Chat] 调用 SadTalker 生成视频（音频={}）...", ttsAudioPath);
                String rawVideoPath = sadTalkerService.generateVideo(sessionId, ttsAudioPath, null, answer, emotion);
                log.info("[Chat] SadTalker 视频生成成功: {}", rawVideoPath);
                // sadTalkerService 返回本地路径，转换为 Python 8001 的 HTTP URL
                videoUrl = "http://localhost:8001/output/" + sessionId + ".mp4";
            } catch (Exception e) {
                videoError = e.getMessage();
                log.error("[Chat] SadTalker 视频生成失败: {}", e.getMessage());
            }

            // Step 4: 返回完整响应
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("sessionId", sessionId);
            response.put("answer", answer);
            response.put("audioUrl", audioUrl);       // TTS 生成的音频 URL
            response.put("videoUrl", videoUrl);         // SadTalker 生成的视频 URL
            response.put("videoError", videoError);
            response.put("emotion", emotion);
            response.put("ragSources", Collections.emptyList());
            response.put("responseTime", 0.0);
            response.put("sadtalkerEnabled", videoUrl != null);

            return ResponseEntity.ok(Result.ok(response));

        } catch (Exception e) {
            log.error("[Chat] 对话处理异常: {}", e.getMessage(), e);
            Map<String, Object> fallback = new LinkedHashMap<>();
            fallback.put("sessionId", sessionId);
            fallback.put("answer", "抱歉，服务暂时出了点问题，请稍后再试。");
            fallback.put("audioUrl", null);
            fallback.put("videoUrl", null);
            fallback.put("emotion", "neutral");
            fallback.put("ragSources", Collections.emptyList());
            fallback.put("sadtalkerEnabled", false);
            return ResponseEntity.ok(Result.ok(fallback));
        }
    }

    /**
     * 旧版兼容：仅对话（不生成视频）
     */
    @ApiOperation("仅对话（兼容旧版）")
    @PostMapping("/chat-only")
    public ResponseEntity<?> chatOnly(@RequestBody Map<String, Object> request) {
        String message = (String) request.getOrDefault("message", "");
        String sessionId = (String) request.getOrDefault("sessionId", "legacy");

        @SuppressWarnings("unchecked")
        List<Map<String, String>> history = (List<Map<String, String>>) request.get("history");

        String answer = llmService.chat(message, history);
        String emotion = llmService.detectEmotion(answer);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("sessionId", sessionId);
        response.put("answer", answer);
        response.put("audioUrl", null);
        response.put("videoUrl", null);
        response.put("emotion", emotion);
        response.put("ragSources", Collections.emptyList());

        return ResponseEntity.ok(Result.ok(response));
    }

    /**
     * 调用 Python TTS 服务生成音频文件
     * @param text 要转换的文本
     * @param sessionId 会话ID（用于文件名）
     * @return 生成的音频文件路径（MP3）
     */
    private String callTTSService(String text, String sessionId) throws Exception {
        // 创建音频存储目录
        Path audioDir = Paths.get("D:/TALKING/scenic-guide-springboot/static/audio");
        Files.createDirectories(audioDir);
        Path audioFile = audioDir.resolve(sessionId + ".mp3");

        // 调用 Python FastAPI TTS 服务
        URL url = new URL("http://localhost:8000/api/voice/tts");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(30000);

        // 构造请求体
        String jsonBody = String.format(
            "{\"text\":\"%s\",\"voice\":\"zh-CN-XiaoxiaoNeural\",\"speed\":1.0}",
            text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", "")
        );

        try (OutputStream os = conn.getOutputStream()) {
            os.write(jsonBody.getBytes("UTF-8"));
        }

        int responseCode = conn.getResponseCode();
        if (responseCode == 200) {
            // 下载音频文件
            try (InputStream is = conn.getInputStream();
                 OutputStream fos = Files.newOutputStream(audioFile)) {
                is.transferTo(fos);
            }
            log.info("[TTS] 音频已保存: {} ({} bytes)", audioFile, Files.size(audioFile));
            return audioFile.toString();
        } else {
            String error = new BufferedReader(new InputStreamReader(conn.getErrorStream()))
                .lines().collect(Collectors.joining());
            throw new RuntimeException("TTS 请求失败: HTTP " + responseCode + " - " + error);
        }
    }

    /**
     * 测试接口
     */
    @ApiOperation("测试接口")
    @GetMapping("/test")
    public Result<Map<String, Object>> test() {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("status", "ok");
        info.put("sadtalkerUrl", "http://localhost:8001");
        info.put("llmConfigured", llmService != null);
        return Result.ok(info);
    }
}
