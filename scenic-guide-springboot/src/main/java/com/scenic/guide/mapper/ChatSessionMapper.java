package com.scenic.guide.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.scenic.guide.entity.ChatSession;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface ChatSessionMapper extends BaseMapper<ChatSession> {

    @Select("SELECT DATE(start_time) as date, COUNT(*) as sessions " +
            "FROM chat_sessions WHERE start_time >= #{since} " +
            "GROUP BY DATE(start_time) ORDER BY DATE(start_time)")
    List<Map<String, Object>> selectDailyStats(java.time.LocalDateTime since);

    @Select("SELECT platform, COUNT(*) as cnt FROM chat_sessions " +
            "WHERE start_time >= #{since} GROUP BY platform")
    List<Map<String, Object>> selectPlatformDistribution(java.time.LocalDateTime since);

    @Select("SELECT AVG(satisfaction_score) FROM chat_sessions " +
            "WHERE start_time >= #{since} AND satisfaction_score IS NOT NULL")
    Double selectAvgSatisfaction(java.time.LocalDateTime since);
}
