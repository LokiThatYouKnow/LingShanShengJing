package com.scenic.guide;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 景区导览AI数字人系统 - Spring Boot 启动类
 */
@SpringBootApplication
@MapperScan("com.scenic.guide.mapper")
public class ScenicGuideApplication {
    public static void main(String[] args) {
        SpringApplication.run(ScenicGuideApplication.class, args);
        System.out.println("==========================================");
        System.out.println("  景区导览AI数字人系统 启动成功！");
        System.out.println("  接口文档: http://localhost:8080/api/doc.html");
        System.out.println("==========================================");
    }
}
