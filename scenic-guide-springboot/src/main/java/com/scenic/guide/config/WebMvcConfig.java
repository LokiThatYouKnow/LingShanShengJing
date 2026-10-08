package com.scenic.guide.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        // Spring MVC 层 CORS — 与 SecurityConfig 保持一致，联合工作
        registry.addMapping("/**")
                .allowedOriginPatterns("http://localhost:*", "http://127.0.0.1:*", "https://*.lucky4u.online")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 静态文件访问 - spot-images 直接访问用户图片目录
        String spotImagesPath = "file:" + "d:/TalkingV2/图片/";
        registry.addResourceHandler("/spot-images/**")
                .addResourceLocations(spotImagesPath);
        // 静态文件访问 - static 目录
        String staticPath = "file:" + "d:/TalkingV2/scenic-guide-springboot/static/";
        registry.addResourceHandler("/static/**")
                .addResourceLocations(staticPath);
        // uploads 目录
        String uploadsPath = "file:" + "d:/TalkingV2/scenic-guide-springboot/uploads/";
        registry.addResourceHandler("/uploads/**")
                .addResourceLocations(uploadsPath);
        // Knife4j
        registry.addResourceHandler("doc.html")
                .addResourceLocations("classpath:/META-INF/resources/");
        registry.addResourceHandler("/webjars/**")
                .addResourceLocations("classpath:/META-INF/resources/webjars/");
    }
}
