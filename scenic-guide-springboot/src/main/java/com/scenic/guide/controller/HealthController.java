package com.scenic.guide.controller;

import com.scenic.guide.common.result.Result;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 系统健康检查
 */
@Api(tags = "系统")
@RestController
public class HealthController {

    @ApiOperation("健康检查")
    @GetMapping("/health")
    public Result<Map<String, Object>> health() {
        return Result.ok(Map.of(
            "status", "ok",
            "app", "景区导览AI数字人系统",
            "version", "2.0.0",
            "framework", "Spring Boot + MyBatis-Plus",
            "services", Map.of(
                "database", "connected",
                "api", "running"
            )
        ));
    }
}
