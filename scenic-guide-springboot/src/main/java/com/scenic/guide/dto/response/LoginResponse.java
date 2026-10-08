package com.scenic.guide.dto.response;

import lombok.Builder;
import lombok.Data;

/**
 * 登录响应
 */
@Data
@Builder
public class LoginResponse {
    private String accessToken;
    private String tokenType;
    private String username;
    private String role;
}
