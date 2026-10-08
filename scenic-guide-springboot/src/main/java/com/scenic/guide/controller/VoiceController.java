package com.scenic.guide.controller;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

/**
 * 语音服务 Controller
 * 代理到 Python TTS/ASR 服务
 */
@Api(tags = "语音服务")
@Slf4j
@RestController
@RequestMapping("/voice")
public class VoiceController {

    @Value("${ai.python-service-url:http://localhost:8000}")
    private String pythonServiceUrl;

    @Value("${ai.enabled:true}")
    private boolean aiEnabled;

    private final RestTemplate restTemplate = new RestTemplate();

    @ApiOperation("文本转语音")
    @PostMapping("/tts")
    public ResponseEntity<?> textToSpeech(@RequestBody Map<String, Object> request) {
        if (!aiEnabled) {
            return ResponseEntity.ok(Map.of("audioUrl", null, "message", "TTS服务未启用"));
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            ResponseEntity<Object> response = restTemplate.exchange(
                    pythonServiceUrl + "/api/voice/tts",
                    HttpMethod.POST, entity, Object.class);
            return ResponseEntity.ok(response.getBody());
        } catch (Exception e) {
            log.warn("TTS服务不可用: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("audioUrl", null, "error", "TTS服务暂时不可用"));
        }
    }

    @ApiOperation("语音识别")
    @PostMapping("/asr")
    public ResponseEntity<?> speechToText(@RequestParam("file") MultipartFile file,
                                          @RequestParam(defaultValue = "zh") String language) {
        if (!aiEnabled) {
            return ResponseEntity.ok(Map.of("text", "语音识别服务未启用"));
        }
        try {
            // 转发到Python ASR服务
            org.springframework.http.client.SimpleClientHttpRequestFactory factory =
                    new org.springframework.http.client.SimpleClientHttpRequestFactory();
            factory.setConnectTimeout(30000);
            factory.setReadTimeout(60000);
            RestTemplate rt = new RestTemplate(factory);

            org.springframework.util.LinkedMultiValueMap<String, Object> body = new org.springframework.util.LinkedMultiValueMap<>();
            body.add("file", new org.springframework.core.io.ByteArrayResource(file.getBytes()) {
                @Override
                public String getFilename() {
                    return file.getOriginalFilename();
                }
            });
            body.add("language", language);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            HttpEntity<org.springframework.util.MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
            ResponseEntity<Object> response = rt.exchange(
                    pythonServiceUrl + "/api/voice/asr",
                    HttpMethod.POST, requestEntity, Object.class);
            return ResponseEntity.ok(response.getBody());
        } catch (Exception e) {
            log.warn("ASR服务不可用: {}", e.getMessage());
            return ResponseEntity.ok(Map.of("text", "", "error", "语音识别服务暂时不可用"));
        }
    }

    @ApiOperation("获取可用音色列表")
    @GetMapping("/voices")
    public ResponseEntity<?> getVoices() {
        return ResponseEntity.ok(Map.of("voices", java.util.List.of(
            "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural",
            "zh-CN-XiaohanNeural", "zh-CN-YunjianNeural",
            "zh-CN-XiaomengNeural", "zh-CN-XiaoyiNeural"
        )));
    }
}
