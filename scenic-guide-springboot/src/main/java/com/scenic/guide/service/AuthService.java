package com.scenic.guide.service;

import com.scenic.guide.dto.request.LoginRequest;
import com.scenic.guide.dto.response.LoginResponse;
import com.scenic.guide.entity.User;

/**
 * 认证 Service 接口
 */
public interface AuthService {
    LoginResponse login(LoginRequest request);
    User getCurrentUser(String username);
}
