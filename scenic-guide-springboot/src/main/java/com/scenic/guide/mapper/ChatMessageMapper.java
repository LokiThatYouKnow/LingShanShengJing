package com.scenic.guide.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.scenic.guide.entity.ChatMessage;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface ChatMessageMapper extends BaseMapper<ChatMessage> {

    @Select("SELECT emotion, COUNT(*) as cnt FROM chat_messages " +
            "WHERE created_at >= #{since} AND role = 'user' AND emotion IS NOT NULL " +
            "GROUP BY emotion")
    List<Map<String, Object>> selectEmotionStats(java.time.LocalDateTime since);

    @Select("SELECT content FROM chat_messages WHERE role = 'user' " +
            "ORDER BY created_at DESC LIMIT 500")
    List<String> selectRecentUserMessages();
}
