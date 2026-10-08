package com.scenic.guide.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;

/**
 * 智谱云（ZhipuAI）LLM 服务
 * 文档: https://open.bigmodel.cn/dev/api
 */
@Slf4j
@Service
public class LlmService {

    @Value("${llm.zhipu-api-key:}")
    private String zhipuApiKey;

    @Value("${llm.zhipu-api-url:https://open.bigmodel.cn/api/paas/v4/chat/completions}")
    private String apiUrl;

    @Value("${llm.enabled:false}")
    private boolean enabled;

    private final RestTemplate restTemplate = new RestTemplate();

    private static final String SYSTEM_PROMPT =
        "你是一位专业、热情的景区AI导游。请根据用户的问题，提供准确、有趣的景区介绍和游览建议。" +
        "回答要简洁生动，一般不超过100字。";

    /**
     * 调用智谱AI生成对话回复
     *
     * @param userMessage 用户消息
     * @param history     历史对话 [{role: "user"|"assistant", content: "..."}]
     * @return AI回复文本
     */
    public String chat(String userMessage, List<Map<String, String>> history) {
        if (!enabled || zhipuApiKey == null || zhipuApiKey.isBlank()) {
            log.warn("[LLM] 智谱API未配置，使用模拟回复");
            return getMockResponse(userMessage);
        }

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + zhipuApiKey);

            List<Map<String, String>> messages = new ArrayList<>();
            messages.add(Map.of("role", "system", "content", SYSTEM_PROMPT));

            if (history != null) {
                for (Map<String, String> h : history) {
                    messages.add(h);
                }
            }
            messages.add(Map.of("role", "user", "content", userMessage));

            Map<String, Object> body = new HashMap<>();
            body.put("model", "glm-4-flash");
            body.put("messages", messages);
            body.put("max_tokens", 200);
            body.put("temperature", 0.7);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                    apiUrl, HttpMethod.POST, entity, Map.class);

            Map<String, Object> respBody = response.getBody();
            if (respBody != null && respBody.containsKey("choices")) {
                List<?> choices = (List<?>) respBody.get("choices");
                if (!choices.isEmpty()) {
                    Map<?, ?> choice = (Map<?, ?>) choices.get(0);
                    Map<?, ?> msg = (Map<?, ?>) choice.get("message");
                    return (String) msg.get("content");
                }
            }
        } catch (Exception e) {
            log.error("[LLM] 智谱API调用失败: {}", e.getMessage());
        }

        return getMockResponse(userMessage);
    }

    /**
     * 模拟回复（当LLM未配置时使用）
     */
    private String getMockResponse(String userMessage) {
        if (userMessage.contains("门票") || userMessage.contains("多少钱")) {
            return "景区门票成人票150元，学生票半价。开放时间为每天8:00-18:00，建议您提前在线购票以避免排队。";
        } else if (userMessage.contains("推荐") || userMessage.contains("必玩")) {
            return "强烈推荐您游览云海日出、奇松怪石和迎客松等经典景点，这些是黄山最不容错过的自然奇观！";
        } else if (userMessage.contains("路线") || userMessage.contains("怎么走")) {
            return "建议从南门云谷寺乘坐索道上山游览北海景区，然后步行至光明顶，傍晚在西海景区观日落，第二天清晨看日出。";
        } else if (userMessage.contains("美食") || userMessage.contains("吃")) {
            return "黄山的毛豆腐、臭鳜鱼和石耳炖鸡是当地特色美食，景区内有多个餐厅，也可以尝尝山下的徽州农家菜。";
        } else if (userMessage.contains("天气") || userMessage.contains("气温")) {
            return "今天黄山风景区晴转多云，山上气温约8-15°C，早晚温差较大，建议携带薄外套和防晒用品。";
        } else {
            return "欢迎来到黄山景区！我是您的AI导游，有任何关于景点、路线、美食的问题都可以问我，我会竭诚为您服务！";
        }
    }

    /**
     * 检测回复情感（简单关键词匹配）
     */
    public String detectEmotion(String text) {
        if (text.contains("推荐") || text.contains("强烈") || text.contains("非常")) {
            return "happy";
        } else if (text.contains("注意") || text.contains("小心") || text.contains("警告")) {
            return "sad";
        } else if (text.contains("！") || text.contains("太棒") || text.contains("惊喜")) {
            return "excited";
        }
        return "neutral";
    }
}
