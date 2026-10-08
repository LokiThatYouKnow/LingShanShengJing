"""
AI对话服务 - 多模态大模型 + RAG + Web搜索兜底
"""
import time
import json
import re
from typing import List, Optional, AsyncGenerator, Dict, Any
from loguru import logger

import httpx

from app.core.config import settings
from app.services.rag_service import rag_service


class AIService:
    """AI对话核心服务"""

    SYSTEM_PROMPT_TEMPLATE = """你是「{avatar_name}」，是无锡灵山胜境景区的AI导游助手。你的名字永远是「{avatar_name}」，任何情况下介绍自己都必须说「{avatar_name}」。

你的职责：
1. 根据灵山胜境景区知识库准确回答游客问题
2. 介绍灵山景点历史文化、佛教艺术、自然风光
3. 推荐个性化游览路线
4. 解答票务、交通、餐饮等实用信息
5. 提供安全提示和游览建议

回答规范：
- 语言生动亲切，像真人导游一样自然
- 回答简洁但信息丰富，每次回答控制在200字以内
- 如果知识库有相关信息，优先使用知识库内容，并保持事实准确
- 如果知识库没有相关信息，请根据你的通用知识来回答，不要提及"知识库"或"向量库"这些词汇
- 对于完全不确定的信息，诚实告知游客，并建议咨询景区工作人员

当前景区：灵山胜境（江苏省无锡市太湖国家旅游度假区）"""

    def _build_system_prompt(self, avatar_name: str = "小灵") -> str:
        """构建系统提示词，使用配置中的数字人名称"""
        name = avatar_name.strip() if avatar_name else "小灵"
        return self.SYSTEM_PROMPT_TEMPLATE.format(avatar_name=name)

    def __init__(self):
        self._openai_client = None
        self._ollama_available = False
        self._init_client()

    def _init_client(self):
        """初始化LLM客户端"""
        try:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            logger.warning(f"OpenAI客户端初始化失败: {e}")

    async def _web_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """联网搜索兜底 — RAG无结果时自动从网络获取信息"""
        results = []

        # 方法1: DuckDuckGo Instant Answer API (无需API key)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    headers={"User-Agent": "ScenicGuideAI/1.0"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # 优先取摘要和相关信息
                    abstract = data.get("Abstract", "").strip()
                    if abstract:
                        results.append({"title": data.get("Heading", query), "snippet": abstract, "source": "DuckDuckGo"})
                    # 取关联主题
                    for topic in data.get("RelatedTopics", [])[:num_results - len(results)]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            snippet = re.sub(r'<[^>]+>', '', topic.get("Text", "")).strip()
                            results.append({"title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "), "snippet": snippet, "source": "DuckDuckGo"})
        except Exception as e:
            logger.info(f"DuckDuckGo搜索失败: {e}")

        # 方法2: DuckDuckGo Lite HTML (备用)
        if not results:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                    resp = await client.get(
                        "https://lite.duckduckgo.com/lite/",
                        params={"q": query},
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    if resp.status_code == 200:
                        # 简单解析 HTML 结果
                        html = resp.text
                        snippets = re.findall(r'<a[^>]*class="result-link"[^>]*>(.*?)</a>.*?<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', html, re.DOTALL)
                        for title, snippet in snippets[:num_results]:
                            title = re.sub(r'<[^>]+>', '', title).strip()
                            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                            if snippet:
                                results.append({"title": title, "snippet": snippet, "source": "DuckDuckGo Lite"})
            except Exception as e:
                logger.info(f"DuckDuckGo Lite搜索失败: {e}")

        # 方法3: Bing 搜索 (国内可访问)
        if not results:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                    resp = await client.get(
                        "https://cn.bing.com/search",
                        params={"q": query + " 灵山胜境"},
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    if resp.status_code == 200:
                        # 解析 Bing 搜索结果
                        html = resp.text
                        blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
                        for block in blocks[:num_results]:
                            title_m = re.search(r'<h2[^>]*><a[^>]*>(.*?)</a>', block, re.DOTALL)
                            snippet_m = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
                            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
                            snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip() if snippet_m else ""
                            if snippet:
                                results.append({"title": title, "snippet": snippet, "source": "Bing"})
            except Exception as e:
                logger.info(f"Bing搜索失败: {e}")

        logger.info(f"Web搜索 '{query[:30]}...' 获取到 {len(results)} 条结果")
        return results[:num_results]

    async def _build_web_context(self, user_message: str) -> str:
        """构建联网搜索上下文"""
        try:
            web_results = await self._web_search(user_message, num_results=5)
            if web_results:
                ctx = "\n\n【联网搜索结果】（注意：以下信息来自网络公开资源，请整合后用于回答）\n"
                for i, r in enumerate(web_results, 1):
                    ctx += f"{i}. {r['snippet'][:300]}\n"
                return ctx
        except Exception as e:
            logger.warning(f"构建联网上下文失败: {e}")
        return ""

    async def _call_llm(
        self,
        messages: List[Dict],
        stream: bool = False,
        avatar_name: str = "小灵"
    ) -> str:
        """调用大语言模型"""

        # 优先使用本地Ollama（如果配置）
        if settings.USE_LOCAL_LLM:
            return await self._call_ollama(messages, avatar_name=avatar_name)

        # 使用OpenAI兼容接口
        if self._openai_client:
            try:
                response = await self._openai_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                    stream=False
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI调用失败: {e}")

        # 兜底：生成基于RAG的模板回复
        return self._fallback_response(messages, avatar_name)

    async def _call_ollama(self, messages: List[Dict], avatar_name: str = "小灵") -> str:
        """调用本地Ollama"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.7}
                    }
                )
                data = resp.json()
                return data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama调用失败: {e}")
            return self._fallback_response(messages, avatar_name)

    def _fallback_response(self, messages: List[Dict], avatar_name: str = "小灵") -> str:
        """无法调用LLM时的兜底响应"""
        user_msg = messages[-1]["content"] if messages else ""
        return (f"感谢您的提问！我是灵山胜境的AI导游{avatar_name}。"
                f"关于「{user_msg[:30]}」，让我为您介绍一下我所知道的："
                f"灵山胜境位于无锡太湖之滨，以88米高的灵山大佛闻名于世，"
                f"拥有梵宫、九龙灌浴、五印坛城等众多景点。"
                f"如果您想了解更详细的信息，建议咨询景区工作人员，或拨打服务热线0510-85680000。")

    async def chat(
        self,
        user_message: str,
        session_id: str,
        history: Optional[List[Dict]] = None,
        context_info: Optional[Dict] = None,
        avatar_name: str = "小灵"
    ) -> Dict[str, Any]:
        """
        主对话接口
        返回: {answer, rag_sources, emotion, response_time}
        """
        start_time = time.time()
        
        # 1. RAG检索
        rag_results = await rag_service.search(user_message, top_k=settings.RAG_TOP_K)

        # 2. 构建上下文
        context_text = ""
        web_searched = False
        if rag_results:
            context_text = "\n\n【景区知识库参考信息】\n"
            for i, r in enumerate(rag_results[:3], 1):
                context_text += f"{i}. {r['content']}\n"
            context_text += "\n请基于以上信息回答游客问题，保证准确性。"
        else:
            # RAG无结果 → 自动联网搜索
            logger.info(f"[AI服务] RAG无结果，触发联网搜索: {user_message[:50]}")
            context_text = await self._build_web_context(user_message)
            if context_text:
                context_text += "\n请基于以上联网搜索结果，整合后回答游客问题（不要提及'搜索'或'网络'）。"
                web_searched = True
            # 若联网也无结果，LLM将使用自身通用知识回答

        # 3. 加入位置/场景信息
        if context_info:
            if context_info.get("spot_name"):
                context_text += f"\n【当前位置】游客正在参观：{context_info['spot_name']}"
            if context_info.get("platform") == "kiosk":
                context_text += "\n【服务场景】景区固定讲解点大屏服务"

        # 4. 构建消息列表
        system_content = self._build_system_prompt(avatar_name) + context_text
        logger.info(f"[AI服务] avatar_name={avatar_name}, system_prompt前80字: {system_content[:80]}")
        messages = [{"role": "system", "content": system_content}]
        
        # 加入历史对话（最近5轮）
        if history:
            for h in history[-10:]:
                messages.append({"role": h["role"], "content": h["content"]})
        
        messages.append({"role": "user", "content": user_message})
        
        # 5. 调用LLM
        answer = await self._call_llm(messages, avatar_name=avatar_name)
        
        # 6. 情感分析
        emotion, emotion_score = await self._analyze_emotion(user_message)
        
        response_time = time.time() - start_time
        
        return {
            "answer": answer,
            "rag_sources": rag_results[:3],
            "emotion": emotion,
            "emotion_score": emotion_score,
            "response_time": round(response_time, 3)
        }

    async def _analyze_emotion(self, text: str) -> tuple:
        """简单情感分析（可替换为专业模型）"""
        positive_words = ["好", "棒", "美", "喜欢", "满意", "不错", "漂亮", "感谢", "谢谢", "开心"]
        negative_words = ["差", "烂", "不好", "失望", "难", "贵", "挤", "累", "热", "不满"]
        
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        
        if pos_count > neg_count:
            return "positive", 0.7 + pos_count * 0.05
        elif neg_count > pos_count:
            return "negative", 0.7 + neg_count * 0.05
        else:
            return "neutral", 0.5

    async def generate_route(
        self,
        preferences: Dict[str, Any],
        available_spots: List[Dict]
    ) -> Dict[str, Any]:
        """AI生成个性化游览路线"""
        spots_desc = "\n".join([
            f"- {s['name']}：{s.get('description', '')[:50]}（建议停留{s.get('duration_minutes', 30)}分钟）"
            for s in available_spots
        ])
        
        pref_str = json.dumps(preferences, ensure_ascii=False)
        
        prompt = f"""游客偏好：{pref_str}
        
可游览景点：
{spots_desc}

请根据游客偏好，生成一个合理的游览路线，包括：
1. 推荐的景点顺序
2. 每个景点的游览要点
3. 预计总时长
4. 注意事项

以JSON格式返回，包含fields: route（景点名称列表）, tips（字符串）, total_hours（数字）"""
        
        messages = [
            {"role": "system", "content": "你是景区智能导游，专业为游客规划游览路线。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._call_llm(messages)
            # 尝试解析JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"路线生成JSON解析失败: {e}")
        
        # 兜底路线
        return {
            "route": [s["name"] for s in available_spots[:4]],
            "tips": "建议按顺序游览，注意补水防晒，保持文明游览。",
            "total_hours": 4.0
        }


# 全局AI服务实例
ai_service = AIService()
